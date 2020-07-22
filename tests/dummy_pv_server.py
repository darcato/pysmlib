from pcaspy import SimpleServer, Driver


class myDriver(Driver):
    def __init__(self):
        super(myDriver, self).__init__()


if __name__ == '__main__':
    prefix = 'CS:'
    pvdb = {
        'al1': {
            'hihi': 10,
            'high':  5,
            'low': -5,
            'lolo': -10
        },
        'al2': {
            'hihi': 10,
            'high':  5,
            'low': -5,
            'lolo': -10
        },
        'wf': {
            'type': 'char',
            'count': 300,
            'value': 'some initial message. but it can become very long.'
        }
    }

    server = SimpleServer()
    server.createPV(prefix, pvdb)
    driver = myDriver()

    while True:
        # process CA transactions
        server.process(0.1)
