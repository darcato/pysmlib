# -*- coding: utf-8 -*-
'''
Timers to awake a fsm after a certain amount of time.

@date: March 26, 2018
@authors: Damiamo Bortolato, Davide Marcato
@email: damiano.bortolato@lnl.infn.it - davide.marcato@lnl.infn.it
'''

import threading
import time


# Classe timer, utilizzabile dalle macchine a stati
class fsmTimer(object):
    def __init__(self, fsm, name):
        self.expire = 0
        self._fsm = fsm
        self._pending = False
        self._name = name

    def reset(self, timeout):
        self.expire = time.time() + timeout
        self._pending = True

    def trigger(self):
        self._pending = False
        self._fsm.trigger(tmrobj=self, timername=self._name, reason="expired")

    def expd(self):
        return not self._pending


# Classe per il management dei timers
class fsmTimers(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        # lock per l'accesso esclusivo
        self._cond = threading.Condition()
        # array con i timers attivi in ordine di scadenza
        # (indice 0 è il prossimo a scadere)
        self._timers = []
        self._stop_thread = False

    # routine principale del thread.
    # Funziona in questo modo: il thread va in sleep per un periodo di tempo pari a quello che manca
    # allo scadere del prossimo timer (il primo di una lista ordinata per scadenza). Allo scadere dello
    # sleep, il thread inizia a vedere quanti timer sono scaduti partendo dal prossimo (possono scaderene
    # anche più di uno quando hanno la stessa ora di scadenza o gli intervalli rientrano nel jitter di
    # esecuzione del thread). Per ogni timer scaduto esegue il trigger e lo rimuove dalla lista dei timer
    # pendenti
    def run(self):
        # acquisisce il lock, per avere accesso esclusivo alla lista dei timer
        self._cond.acquire()
        next_wait = None
        while not self._stop_thread:
            if len(self._timers):  # se ci sono timers in pendenti
                now = time.time()  # tempo corrente
                i = 0
                next_wait = None
                for t in self._timers:
                    if t.expire > now:
                        # abbiamo trovato il primo timer non ancora scaduto,
                        # interrompo la scansione, i rappresenta l'indice del primo timer non scaduto
                        next_wait = self._timers[i].expire - now
                        break
                    i += 1
                # triggera gli eventi per i timer che vanno da 0 a i-1
                for t in self._timers[:i]:
                    t.trigger()
                # rimuove i primi 'i' timers (che sono scaduti)
                self._timers = self._timers[i:]
            # va in sleep per i prossimi 'next_wait' secondi, ovvero l'intervallo di tempo al termine del quale scadra'
            # il prossimo timer. Se non ci sono timer va in sleep a per un tempo indefinito
            # NB: wait rilascia il lock permettendo ad altri thread di impostare altri timer
            self._cond.wait(next_wait)

    # imposta un timer
    def set(self, timer, timeout, reset=True):
        # ottiene l'accesso esclusivo alla lista dei timer
        self._cond.acquire()
        try:
            # se il timer è già in lista significa che è stato reimpostato prima che scadesse,
            # quindi lo rimuovo e lo reimposto
            if timer in self._timers:
                if not reset:
                    # timer già settato e non è richiesto reset, ritorno (il release() della
                    # condizione è in finally:
                    return
                self._timers.remove(timer)

            # imposta il tempo al quale scadrà il timer
            timer.reset(timeout)

            i = 0
            for t in self._timers:
                if t.expire > timer.expire:
                    # il timer all'indice 'i' scade dopo il timer che sto impostando, pertanto
                    # inserisco il nuovo timer in questa posizione 'i' e interrompo il ciclo
                    break
                i += 1
            self._timers.insert(i, timer)
            if i == 0:
                # CASO SPECIALE: se 'i'  == 0 significa che ho inserito in testa il nuovo timer oppure l'ho inserito
                # in una lista vuota; nel primo caso devo svegliare il thread perche' il nuovo timer scadra' prima
                # del suo prossimo risveglio (impostato su quello che ora è il secondo timer in lista), nel secondo
                # caso il thread sta dormendo per un tempo indefinito, quindi lo devo svegliare affinche reimposti
                # un tempo di sleep corretto
                self._cond.notify()
            # rilascia il lock
        except Exception as e:
            print(repr(e))
        finally:
            self._cond.release()

    def kill(self):
        self._cond.acquire()
        self._stop_thread = True
        self._cond.notify()
        self._cond.release()
        self.join()
