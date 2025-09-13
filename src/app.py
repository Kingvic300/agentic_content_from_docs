from dotenv import load_dotenv
load_dotenv()
from flask import Flask
from controllers.content_generator_controller import content_bp
from mongoengine import connect
from configuration.configuration import Configuration

app = Flask(__name__)
app.config['MONGODB_SETTINGS'] = {
    'db': 'content_gen',
    'host': Configuration.mongo_uri
}
connect(**app.config['MONGODB_SETTINGS'])
app.register_blueprint(content_bp)

if __name__ == "__main__":
    app.run(debug=True)