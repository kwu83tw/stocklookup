import bottle
from api import snames

app = application = bottle.default_app()

if __name__ == '__main__':
    bottle.run(host='127.0.0.1', port=8099, debug=True)
