from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
import pandas as pd
import openai
from sqlalchemy.sql import text
from dotenv import load_dotenv
import subprocess
import threading
import secrets
import time

# Generate a secret key
secret_key = secrets.token_hex(16)
print(secret_key)

app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key
socketio = SocketIO(app)

# Database setup
Base = declarative_base()
DBServerName = "LUCA"
DBName = "FinalRedditDataDB"

# Correct the connection string
connection_string = f"mssql+pyodbc://{DBServerName}/{DBName}?driver=ODBC%20Driver%2017%20for%20SQL%20Server&trusted_connection=yes"

# Create the database engine
engine = create_engine(connection_string)
Session = sessionmaker(bind=engine)
session = Session()

# SQLAlchemy models
class Subreddit(Base):
    __tablename__ = 'tblSubreddit'
    SubredditID = Column('tblSubreddit_SubredditID', String(50), primary_key=True)
    Name = Column('tblSubreddit_Name', String(100), nullable=False)
    IconImg = Column('tblSubreddit_IconImg', Text)
    Subscribers = Column('tblSubreddit_Subscribers', Integer)
    ActiveUsers = Column('tblSubreddit_ActiveUsers', Integer)

class Post(Base):
    __tablename__ = 'tblPost'
    PostID = Column('tblPost_PostID', String(50), primary_key=True)
    Title = Column('tblPost_Title', String(300), nullable=False)
    TitleSentiment = Column('tblPost_TitleSentiment', Float)
    AuthorID = Column('tblPost_AuthorID', String(50))
    SubredditID = Column('tblPost_SubredditID', String(50), ForeignKey('tblSubreddit.tblSubreddit_SubredditID'))
    Content = Column('tblPost_Content', Text)
    ContentSentiment = Column('tblPost_ContentSentiment', Float)
    URL = Column('tblPost_URL', Text)
    ImageURL = Column('tblPost_ImageURL', Text)
    Score = Column('tblPost_Score', Integer)
    UpvoteRatio = Column('tblPost_UpvoteRatio', Float)
    NumComments = Column('tblPost_NumComments', Integer)
    CreatedUTC = Column('tblPost_CreatedUTC', DateTime)
    Permalink = Column('tblPost_Permalink', Text)
    Distinguished = Column('tblPost_Distinguished', String(50))
    Stickied = Column('tblPost_Stickied', Boolean)
    Edited = Column('tblPost_Edited', Boolean)
    IsOriginalContent = Column('tblPost_IsOriginalContent', Boolean)
    Gilded = Column('tblPost_Gilded', Integer)
    IsSelf = Column('tblPost_IsSelf', Boolean)
    LinkFlairText = Column('tblPost_LinkFlairText', String(255))
    ImageDescription = Column('tblPost_ImageDescription', Text)
    ImageDescriptionSentiment = Column('tblPost_ImageDescriptionSentiment', Float)
    
    subreddit = relationship('Subreddit', backref='posts')

@app.route('/')
def home():
    subreddit_names = ['ValueInvesting', 'WallStreetBets', 'Robinhood', 'CryptoCurrency']
    subreddits = session.query(Subreddit).filter(Subreddit.Name.in_(subreddit_names)).all()
    schwab_posts = session.query(Post).join(Subreddit).filter(Post.Title.like('%Schwab%')).order_by(Post.CreatedUTC.desc()).limit(5).all()
    return render_template('index.html', subreddits=subreddits, schwab_posts=schwab_posts)

@app.route('/get_table_data', methods=['GET'])
def get_table_data():
    table_name = request.args.get('table')
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql(query, engine)
    table_html = df.to_html(classes='dataframe table table-striped', index=False)
    return table_html

@app.route('/get-sql-code')
def get_sql_code():
    with open('FinalRedditDataDB.sql', 'r') as file:
        sql_code = file.read()
    return sql_code

@app.route('/nlp2sql')
def nlp2sql():
    return render_template('NLP2SQL.html')

# Load OpenAI API Key
load_dotenv('.env')
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/generate-sql', methods=['POST'])
def generate_sql():
    natural_language_query = request.json.get('query')
    if natural_language_query:
        try:
            sql_query = nlp_to_sql(natural_language_query)
            results = execute_sql_query(sql_query)
            return jsonify({'sql': sql_query, 'results': results})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'No query provided'}), 400

def nlp_to_sql(natural_language_query):
    # Read the entire SQL file content
    try:
        with open('FinalRedditDataDB.sql', 'r') as file:
            sql_schema = file.read()
    except Exception as e:
        return f"Failed to read SQL schema file: {e}"

    # Prepare the prompt for the OpenAI model
    prompt = f"You are an assistant that translates natural language queries into SQL queries for MSSQL. You can ONLY output queries, NOT other text." \
             f"Here is the database schema you need to use:\n\n{sql_schema}\n\n" \
             f"Translate the following natural language query into an SQL query:\n\n{natural_language_query}" 

    # Call OpenAI API
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=150,
        n=1,
        stop=None,
        temperature=0
    )
    sql_query = response.choices[0].message['content'].strip()
    return sql_query.replace('```sql', '').replace('```', '').strip()

def execute_sql_query(sql_query):
    session = Session()
    try:
        result = session.execute(text(sql_query)).fetchall()
        session.commit()
        return [dict(row) for row in result]
    except Exception as e:
        session.rollback()
        print(f"Error executing query: {e}")
        return []
    finally:
        session.close()

@app.route('/run-query', methods=['POST'])
def run_query():
    data = request.get_json()
    query = data.get('query')
    df = pd.read_sql(query, engine)
    table_html = df.to_html(classes='dataframe table table-striped', index=False)
    return jsonify({'table': table_html})

@app.route('/data')
def data_page():
    return render_template('data.html')

process = None

@socketio.on('start_script')
def handle_start_script():
    global process
    if process is None:
        process = subprocess.Popen(
            ['python', 'FinalMain.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        thread = threading.Thread(target=stream_output, args=(process,))
        thread.start()
        print("Script started")

@socketio.on('stop_script')
def handle_stop_script():
    global process
    if process:
        process.terminate()
        process = None
        socketio.emit('script_output', {'data': 'Script terminated.'})
        print("Script stopped")

def stream_output(process):
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            socketio.emit('script_output', {'data': output})
            print(f"Output: {output.strip()}")
    stderr = process.stderr.read()
    if stderr:
        socketio.emit('script_output', {'data': stderr, 'error': True})
        print(f"Error: {stderr.strip()}")

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

@socketio.on('start_stream')
def handle_start_stream():
    print("start_stream event received")
    query = text("SELECT tblComment_CreatedUTC, tblComment_ContentSentiment FROM tblComment")
    result = session.execute(query)
    data = [{'x': row[0].isoformat(), 'y': row[1]} for row in result]
    emit('initial_data', data)
    print("Initial data sent")

latest_data = None  # Initialize latest_data at the beginning

def fetch_new_data():
    global latest_data
    session = Session()
    query = text("SELECT TOP 1 tblComment_CreatedUTC, tblComment_ContentSentiment FROM tblComment ORDER BY tblComment_CreatedUTC DESC")
    result = session.execute(query).fetchone()
    if result:
        new_data = {'x': result[0].isoformat(), 'y': result[1]}
        if latest_data is None or new_data != latest_data:
            latest_data = new_data
            socketio.emit('new_data', new_data)
            print("New data sent", new_data)
    session.close()

def continuous_fetch():
    while True:
        fetch_new_data()
        time.sleep(1)  # Adjust the sleep time as needed

if __name__ == '__main__':
    threading.Thread(target=continuous_fetch, daemon=True).start()
    socketio.run(app, debug=True)
