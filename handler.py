import os
import json
import requests
import mysql.connector
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from datetime import datetime

app = Flask(__name__)

PART_A = 0
PART_B = 1


class SpeechAceHandler:
    def __init__(self, api_key) -> None:  
        self.api_key = api_key
        self.api_endpoint = "https://api2.speechace.com" 
        self.dialect = "en-us"
        self.user_id = "qef_web"
        
        self.premium_url =  self.api_endpoint + "/api/scoring/speech/v9/json" + \
                    '?' + 'key=' + self.api_key + \
                    '&dialect=' + self.dialect + \
                    '&user_id=' + self.user_id
        
        
    def send_premium_request(self, audio):
        payload ={
            'include_fluency': '1', 
            'include_intonation': '1',
            'include_ielts_subscore': '1',
            'include_ielts_feedback': '1',
        }
        files = {'user_audio_file': audio}
        response = requests.post(self.premium_url, data=payload, files=files)
        result = json.loads(str(response.text))
        result = json.dumps(result, indent=4)
        return result



class MockTestHandler:
    def __init__(self, host, user, passwd, db) -> None:
        self.database = mysql.connector.connect(
                        host=host,
                        user=user,
                        password=passwd,
                        database=db
                    )
        self.table_A = 'PartA'
        self.table_B = 'PartB'
        
    
    def __del__(self):
        self.database.close()
        
    
    def create_new_test(self, start_time):
        cursor = self.database.cursor()        
        
        query = "INSERT INTO (%s) (start_time) VALUES (%s)"        
        cursor.execute(query, (self.table_A, start_time,))
        id_A = cursor.lastrowid
        cursor.execute(query, (self.table_B, start_time,))
        id_B = cursor.lastrowid
        
        cursor.close()
        self.database.commit()
        return id_A, id_B
    
    
    def enquire_SpeechAce_part_result(self, id, part):        
        cursor = self.database.cursor()
        
        query = "SELECT speechace_json FROM %s WHERE id = %s"
        table = self.table_A if part == PART_A else self.table_B
        cursor.execute(query, (table, id,))
        result = cursor.fetchone()

        cursor.close()
        if result is not None:
            return result[0]
        else:
            return None
        
        
    def upload_part_data(self, id, part, video_link, audio_link, upload_time, speechace_json):
        try:
            cursor = self.database.cursor()
            
            query = "UPDATE %s SET video_link = %s, audio_link = %s, upload_time = %s, speechace_json = %s WHERE id = %s"
            table = self.table_A if part == PART_A else self.table_B
            cursor.execute(query, (table, video_link, audio_link, upload_time, speechace_json, id))
            
            cursor.close()
            self.database.commit()
            return True
        except Exception as e:
            print(e)
            return False


      
load_dotenv()
api_key = os.getenv("SPEECHACE_API_KEY")
db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_passwd = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")

mSpeechAceHandler = SpeechAceHandler(api_key)
mMockTestHandler = MockTestHandler(db_host, db_user, db_passwd, db_name)


@app.route('/create_test', methods=['POST'])
def create_test():  
    start_time = datetime.now().timestamp() # float
    id_A, id_B = mMockTestHandler.create_new_test(start_time)
    return [id_A, id_B] # jsonify({"id_A": id_A, "id_B": id_B})


@app.route('/upload_data', methods=['POST'])
def upload_data():   
    id = request.form['id']
    part = request.form['part']      
    video_file = request.files['video']
    audio_file = request.files['audio']
    
    '''
    upload to cloud storage, and get the links
    '''
    video_link = '' # cloud storage link
    audio_link = '' # cloud storage link
    
    upload_time = datetime.now().timestamp() # float   
    speechace_json = mSpeechAceHandler.send_premium_request(audio_file)
    return mMockTestHandler.upload_part_data(id, part, video_link, audio_link, upload_time, speechace_json)
    
    
@app.route('/get_part_result', methods=['POST'])
def get_part_result():  
    id = request.form['id']
    part = request.form['part']
    return mMockTestHandler.enquire_SpeechAce_part_result(id, part)




    
if __name__ == '__main__':
    app.run()