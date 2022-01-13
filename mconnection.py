import sys
import mysql.connector
from mysql.connector import Error

def establish_connection(log, online = False):
    version = sys.version_info
    if not online:
        try:
            connection = mysql.connector.connect(host='127.0.0.1',
                                                database='economics',
                                                user='marcin',
                                                password='econtheory',
                                                port = '33360',
                                                buffered = True)
            if connection.is_connected():
                db_Info = connection.get_server_info()
                cursor = connection.cursor()
                cursor.execute("select database();")
                record = cursor.fetchone()
                return connection, cursor
        except Error as e:
            log.add_line(["-"*20,"-"*20,"-"*20])
            log.add_line(["Error while connecting to MySQL", e])
            log.add_line(["This connection should work from outside of LM. If it doesn't work, you probably forgot to set up VAGRANT"])
    else:
        try:
            #This connection is from inside of vagrant machine, or maybe even from 
            connection = mysql.connector.connect(host='localhost',
                                                database='economics',
                                                user='www',
                                                password='1www',
                                                port = '3306',#33360 - see above
                                                buffered = True)
            if connection.is_connected():
                db_Info = connection.get_server_info()
                log.add_line(["Connected to MySQL Server version ", db_Info])
                cursor = connection.cursor()
                cursor.execute("select database();")
                record = cursor.fetchone()
                log.add_line(["You're connected to database: ", record])
                return connection, cursor
        except Error as e:
            log.add_line(["-"*20,"-"*20,"-"*20])
            log.add_line(["Error while connecting to MySQL", e])
            log.add_line(["This connection should work from outside of LM. If it doesn't work, you probably forgot to set up VAGRANT"])
        

def close_connection(connection, cursor, commit = False):
    if (connection.is_connected()):
        if commit:
            connection.commit()
        cursor.close()
        connection.close()
