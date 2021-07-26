import os, glob
from datetime import datetime as dt
from datetime import timedelta

from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

import pandas as pd

fs = glob.glob(os.path.join(os.getcwd(),'data','*_forecast.csv'))
dfs_forecast = {os.path.splitext(os.path.split(f)[1])[0].split('_')[0]:pd.read_csv(f).set_index('index') for f in fs}
fs = glob.glob(os.path.join(os.getcwd(),'data','*_historic.csv'))
dfs_historic = {os.path.splitext(os.path.split(f)[1])[0].split('_')[0]:pd.read_csv(f).set_index('Unnamed: 0') for f in fs}
for kk in dfs_forecast.keys():
    dfs_forecast[kk].index = pd.to_datetime(dfs_forecast[kk].index)
    dfs_historic[kk].index = pd.to_datetime(dfs_historic[kk].index)
    dfs_historic[kk]['x'] = dfs_historic[kk].index.astype(str)
    dfs_historic[kk].rename(columns={'PRESENT_STORAGE_TMC':'y'}, inplace=True)

app = Flask(__name__)
auth = HTTPBasicAuth()

CORS(app)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

users = {
    os.environ['USERNAME']: generate_password_hash(os.environ['USERPASSWORD'])
}

@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username

@app.route('/api/')
@auth.login_required
def index():
    reservoir = request.args.get('reservoir')
    if reservoir is None or reservoir not in dfs_historic.keys():
        return jsonify({'error':f'specify a reservoir from {dfs_historic.keys()}'})
    date = request.args.get('date')
    try:
        date = dt.strptime(date,'%Y-%m-%d')
    except:
        return jsonify({'error':f'specify a date as YYYY-MM-DD'})

    try:

        projections = [
            {
                'x':str(date+timedelta(days=int(kk.split(' ')[0])))[0:10],
                'y':vv
            } 
            for kk,vv in dfs_forecast[reservoir].loc[date,:].to_dict().items()
        ]

        data = {
            'historic':dfs_historic[reservoir].loc[(dfs_historic[reservoir].index>(date-timedelta(days=90))) & (dfs_historic[reservoir].index<=(date)),['x','y']].to_dict(orient='records'),
            'future':dfs_historic[reservoir].loc[(dfs_historic[reservoir].index>(date)) & (dfs_historic[reservoir].index<=(date+timedelta(days=90))),['x','y']].to_dict(orient='records'),
            'predicted':projections
        }
        return jsonify(data)
        
    except Exception as e:
        print ('Error!',e)
        return jsonify({'Error':f'bad request: {e}'})

    

if __name__ == '__main__':
    app.run()
