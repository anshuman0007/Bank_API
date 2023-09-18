from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt

app=Flask(__name__)
api=Api(app)

client=MongoClient("mongodb://db:27017")
db= client.BankAPI
users=db["Users"]

def UserExists(username):
    if users.count_documents({"Username":username})==0:
        return False
    else:
        return True
    
class Register(Resource):
    def post(self):
        postedData=request.get_json()

        username=postedData["username"]
        password=postedData["password"]

        if UserExists(username):
            retJson={
                "status":"301",
                "message":"Invalid Username"
            }
            return jsonify(retJson)
        
        hashed_pw=bcrypt.hashpw(password.encode('utf8'),bcrypt.gensalt())

        users.insert_one({
            "Username":username,
            "Password": hashed_pw,
            "Own": 0,
            "Debt":0
        })

        retJson={
            "status":200,
            "msg": "Welcome to the Bank Api"
        }
        return jsonify(retJson)

def verifyPw(username, password):
    if not UserExists(username):
        return False    

    hashed_pw=users.find({
        "Username":username
    })[0]["Password"]

    if bcrypt.hashpw(password.encode('utf8'),hashed_pw)==hashed_pw:
        return True
    else:
        return False

def cashWithUser(username):
    balance=users.find({
        "Username":username
    })[0]["Own"]
    return balance

def debtwithUser(username):
    debt=users.find({
        "Username":username
    })[0]["Debt"]
    return debt

def generateReturnDictionary(status,msg):
    retJson={
        "status":status,
        "msg":msg
    }
    return retJson

#Error Dictionary, True/False
def verifyCredentials(username, password):
    if not UserExists(username):
        return generateReturnDictionary(301, "Invalid Username"), True
    
    correct_pw=verifyPw(username,password)

    if not correct_pw:
        return generateReturnDictionary(302,"Incorrect Password"), True
    
    return None, False

def updateAccount(username, balance):
    users.update_one({
        "Username":username
    },{
        "$set":{
            "Own": balance
        }
    })

def updateDebt(username,balance):
    users.update_one({
        "Username":username,
    },{
        "$set":{
            "Debt":balance
        }
    })

class Add(Resource):
    def post(self):
        postedData=request.get_json()
        username=postedData["username"]
        password=postedData["password"]
        money=postedData["amount"]

        retJson, error=verifyCredentials(username, password)

        if error:
            return jsonify(retJson) 

        if money<=0:
            return jsonify(generateReturnDictionary(304,"The amount entered must be > 0")) 
        cash= cashWithUser(username)
        money-=1
        bank_cash=cashWithUser("BANK")
        updateAccount("BANK",bank_cash+1)
        updateAccount(username,cash+money)

        return jsonify(generateReturnDictionary(200, "Amount added successfully to account"))


class Transfer(Resource):
    def post(self):
        postedData=request.get_json()
        username=postedData["username"]
        password=postedData["password"]
        transfer_to=postedData["transfer_to"]
        money=postedData["amount"]

        retjson,error=verifyCredentials(username,password)

        if error:
            return jsonify(retjson)
        
        cash=cashWithUser(username)
        
        if money>=cash:
            return jsonify(generateReturnDictionary(304,"Insufficient funds, please add or take a loan"))
        
        if not UserExists(transfer_to):
            return jsonify(generateReturnDictionary(301,"Receiver username is invalid"))
        
        cash_from=cashWithUser(username)
        cash_to= cashWithUser(transfer_to)
        bank_cash=cashWithUser("BANK")

        updateAccount("BANK",bank_cash+1)
        updateAccount(transfer_to, cash_to+money-1)
        updateAccount(username, cash_from-money)

        return jsonify(generateReturnDictionary(200,"Amount Transferred successfully"))
    
class Balance(Resource):
    def post(self):
        postedData=request.get_json()
        username=postedData["username"]
        password=postedData["password"]

        retJson, error=verifyCredentials(username,password)

        if error:
            return jsonify(retJson)
        
        retJson=users.find({
            "Username":username
        },{
            "Password":0,
            "_id":0
        })[0]

        return jsonify(retJson)

class TakeLoan(Resource):
    def post(self):
        postedData=request.get_json()

        username=postedData["username"]
        password=postedData["password"]
        money=postedData["amount"]

        retJson, error=verifyCredentials(username,password)

        if error:
            return jsonify(retJson)
        
        cash=cashWithUser(username)
        debt=debtwithUser(username)
        updateAccount(username,cash+money)
        updateDebt(username,debt+money)

        return jsonify(generateReturnDictionary(200,"Loan added to your account"))
    
class PayLoan(Resource):
    def post(self):
        postedData=request.get_json()

        username=postedData["username"]
        password=postedData["password"]
        money=postedData["amount"]

        retJson,error=verifyCredentials(username,password)

        if error:
            return jsonify(retJson)
        
        cash=cashWithUser(username)

        if cash<money:
            return jsonify(generateReturnDictionary(303,"Not enough cash in your account"))
        
        debt=debtwithUser(username)

        updateAccount(username, cash-money)
        updateDebt(username,debt-money)

        return jsonify(generateReturnDictionary(200, "You have successfully paid your loan"))

api.add_resource(Register, '/register')
api.add_resource(Add, '/add')
api.add_resource(Transfer,'/transfer')
api.add_resource(Balance,'/balance')
api.add_resource(TakeLoan,'/takeloan')
api.add_resource(PayLoan,'/payloan')

if __name__=="__main__":
    app.run(host='0.0.0.0')