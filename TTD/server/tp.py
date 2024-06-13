from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import AutoTokenizer, AutoModelForCausalLM
import mysql.connector
import re

app = Flask(__name__)
CORS(app)

def chat_template(question, context):
    """
    Creates a chat template for the Llama model.

    Args:
        question: The question to be answered.
        context: The context information to be used for generating the answer.

    Returns:
        A string containing the chat template.
    """

    template = f"""\
    user
    Given the context, generate an SQL query for the following question.
    context:{context}
    question:{question}
    
    assistant 
    """
    template = "\n".join([line.lstrip() for line in template.splitlines()])
    return template

model_path = "D:/CODES/Final-Project/drive/FinalProjectModel"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(model_path)

def get_table_info():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="company"
        )
        cursor = connection.cursor()
        print("Connected to MySQL database successfully.")
        
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        table_info = []
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            columns = cursor.fetchall()
            column_info = []
            for column in columns:
                column_name = column[0]
                data_type = column[1]
                column_info.append(f"{column_name} {data_type}")
            table_info.append(f"CREATE TABLE {table_name} ({', '.join(column_info)})")

        print("Table information fetched successfully.")
        cursor.close()
        connection.close()
        return table_info
    
    except mysql.connector.Error as error:
        print("Error while connecting to MySQL database:", error)
        return None

tablecontext=""
table_info = get_table_info()
if table_info:
    for sql_string in table_info:
        tablecontext+=sql_string
else:
    print("Failed to fetch table information from the database.")

def generate_sql_query(question):
    context = tablecontext
    prompt = chat_template(question, context)
    inputs = tokenizer(prompt, return_tensors="pt")
    output = model.generate(**inputs, max_length=512)
    text = tokenizer.decode(output[0], skip_special_tokens=True)
    query_texts = text.split("assistant")[1:]
    first_query_text = query_texts[0].strip()
    final_query = first_query_text.split(";")[0].strip() + ";"
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

def extract_table_name(query):
    match = re.search(r'(?:insert into|update|delete from)\s+([^\s;]+)', query, re.IGNORECASE)
    if match:
        return match.group(1)
    else:
        return None
    
def execute_query_on_database(query):
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="company"
        )
        cursor = connection.cursor()
        cursor.execute(query)
        
        if query.strip().lower().startswith('select'):
            result = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            return result, column_names
        elif query.strip().lower().startswith('create'):
            return "Table created successfully", None
        elif query.strip().lower().startswith('insert') or query.strip().lower().startswith('update') or query.strip().lower().startswith('delete'):
            tablename = extract_table_name(query)
            if tablename:
                spquery = f'SELECT * FROM {tablename};'
                cursor.execute(spquery)
                result = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                connection.commit() 
                cursor.fetchall()  
                return result, column_names
            else:
                return "Unable to determine table name from query", None
        else:
            return "Unsupported query type", None
        
    except mysql.connector.Error as error:
        print("Error while executing SQL query:", error)
        return None, None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/execute-sql-query', methods=['POST'])
def execute_sql_query_route():
    data = request.get_json()
    query = data.get('query')
    if query:
        result, column_names = execute_query_on_database(query)
        if result is not None and column_names is not None:
            return jsonify({'result': result, 'column_names': column_names}), 200
        else:
            return jsonify({'error': 'Error executing SQL query'}), 500 
    else:
        return jsonify({'error': 'Query not provided'}), 400

if __name__ == '__main__':
    app.run(debug=True)