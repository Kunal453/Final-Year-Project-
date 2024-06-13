from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import AutoTokenizer, AutoModelForCausalLM
import mysql.connector
import re

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    'host': "localhost",
    'user': "root",
    'password': "root",
    'database': "company"
}

model_path = r"D:\CODES\Final-Project\TTD\server\model"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(model_path)

def connect_to_db():
    """Connects to the MySQL database."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        print("Connected to MySQL database successfully.")
        return connection, cursor
    except mysql.connector.Error as error:
        print("Error while connecting to MySQL database:", error)
        return None, None

def get_table_info():
    """Fetches table information from the database."""
    connection, cursor = connect_to_db()
    if connection and cursor:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        table_info = []
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            columns = cursor.fetchall()
            column_info = [f"{column[0]} {column[1]}" for column in columns]
            table_info.append(f"CREATE TABLE {table_name} ({', '.join(column_info)})")
        print("Table information fetched successfully.")
        cursor.close()
        connection.close()
        return table_info
    return None

def generate_sql_query(question):
    """Generates an SQL query using the Llama model."""
    context = "\n".join(get_table_info() or [])
    prompt = f"user\nGiven the context, generate an SQL query for the following question.\ncontext:{context}\nquestion:{question}\n\nassistant"
    inputs = tokenizer(prompt, return_tensors="pt")
    output = model.generate(**inputs, max_length=512)
    text = tokenizer.decode(output[0], skip_special_tokens=True)
    query_texts = text.split("assistant")[1:]
    first_query_text = query_texts[0].strip()
    final_query = first_query_text.lstrip(':').strip().split(";")[0].strip() + ";"
    return final_query

@app.route('/generate-sql-query', methods=['POST'])
def generate_sql_query_route():
    data = request.get_json()
    question = data.get('question')
    if question:
        final_query = generate_sql_query(question)
        return jsonify({'sql_query': final_query}), 200
    else:
        return jsonify({'error': 'Question not provided'}), 400

def execute_query_on_database(query):
    """Executes an SQL query on the database and returns the result."""
    connection, cursor = connect_to_db()
    if connection and cursor:
        cursor.execute(query)
        if query.strip().lower().startswith('select'):
            result = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            return result, column_names
        elif query.strip().lower().startswith('create'):
            return "Table created successfully", None
        elif query.strip().lower().startswith(('insert', 'update', 'delete')):
            tablename = extract_table_name(query)
            if tablename:
                spquery = f'SELECT * FROM {tablename};'
                cursor.execute(spquery)
                result = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                connection.commit()
                return result, column_names
            else:
                return "Unable to determine table name from query", None
        else:
            return "Unsupported query type", None
    else:
        return None, None

def extract_table_name(query):
    """Extracts the table name from an SQL query."""
    match = re.search(r'(?:insert into|update|delete from)\s+([^\s;]+)', query, re.IGNORECASE)
    return match.group(1) if match else None

@app.route('/execute-sql-query', methods=['POST'])
def execute_sql_query_route():
    data = request.get_json()
    query = data.get('query')
    if query:
        result, column_names = execute_query_on_database(query)
        if result is not None:
            if isinstance(result, str):
                return jsonify({'result': result}), 200
            else:
                return jsonify({'result': result, 'column_names': column_names}), 200
        else:
            return jsonify({'error': 'Error executing SQL query'}), 500 
    else:
        return jsonify({'error': 'Query not provided'}), 400


if __name__ == '__main__':
    app.run(debug=True)
