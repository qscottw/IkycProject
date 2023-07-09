import sys
import cv2
import mysql.connector
from mysql.connector import Error
import face_recognition
import os
import threading
import numpy as np
import pyttsx3
import pickle
import logging
from datetime import date, datetime
import re
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
import requests

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

# setting up db access
dbconf={
    'host':'localhost',
    'database':'ikyc_system_new',
    'user':'root',
    'password':'scott6123456'
}
logging.basicConfig(level=logging.DEBUG)

try:
    connection=mysql.connector.connect(**dbconf)
    if connection.is_connected():
            db_Info = connection.get_server_info()
            logging.debug("Connected to MySQL Server version ", db_Info)
            cursor = connection.cursor()
            cursor.execute("select database();")
            record = cursor.fetchone()
            logging.debug("You're connected to database: ", record)
except Error as e:
    logging.debug("Error connecting to database", e)

btn_style = 'QPushButton {background-color: #00a86c; border: none; color: #ffffff; font-family: ubuntu, arial; font-size: 16px;}' \
            'QPushButton::hover {background-color:#b35334; border:none; color: #ffffff; font-family: ubuntu, arial; font-size: 16px;}'
input_style = 'QLineEdit {border: 1px solid #c8c8c8; font-family: ubuntu, arial; font-size: 14px;}'
error_style = 'QLineEdit {border: 1px solid #fc0000; font-family: ubuntu, arial; font-size: 14px;}'
error_style_c='QComboBox {border: 1px solid #fc0000; font-family: ubuntu, arial; font-size: 14px;}'

#setting up email service
my_sg=sendgrid.SendGridAPIClient(api_key="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")
from_email=Email("u3563881@connect.hku.hk")

face_cascade=cv2.CascadeClassifier('haarcascade/haarcascade_frontalface_default.xml')

class UIInfoTab(object):
    def __init__(self, MainWindow):
        self.MainWindow=MainWindow

    def setupUI(self, username):
        #  are not thread safe so can be only modified in the main thread
        self.username=username
        self.centralwidget = QWidget(self.MainWindow)
        sql_name="select name from customer where user_name='{}'".format(username)
        cursor.execute(sql_name)
        nameres=cursor.fetchall()
        self.MainWindow.setWindowTitle("Hello, {}, welcome to the IKYC system".format(nameres[0][0]))
        menuBar=QMenuBar(self.MainWindow)
        self.MainWindow.setMenuBar(menuBar)
        viewMenu = menuBar.addMenu("View")
        self.viewAccountAction=QAction("Accounts", self.MainWindow)
        self.viewAccountAction.triggered.connect(self.showAccount)
        self.viewLoginHistoryAction=QAction("Login History", self.MainWindow)
        self.viewLoginHistoryAction.triggered.connect(self.showHistory)
        viewMenu.addAction(self.viewAccountAction)
        viewMenu.addAction(self.viewLoginHistoryAction)
        settingMenu = menuBar.addMenu("Setting")
        self.logoutAction=QAction("Logout", self.MainWindow)
        settingMenu.addAction(self.logoutAction)
        self.logoutAction.triggered.connect(self.logout)
        self.refreshAction=QAction("Refresh")
        settingMenu.addAction(self.refreshAction)
        self.refreshAction.triggered.connect(self.refresh)
        sql_email="select email from customer where user_name='{}'".format(self.username)
        cursor.execute(sql_email)
        self.email=cursor.fetchall()[0][0]
        self.viewAccountAction.trigger()

    def showAccount(self):
        self.centralwidget=QWidget(self.MainWindow)
        # contents of the info page
        self.add_btn = QPushButton("Add account")
        self.make_btn=QPushButton("Make transaction")
        self.link_btn=QPushButton("Link account")
        self.add_btn.setMinimumHeight(40)
        self.make_btn.setMinimumHeight(40)
        self.link_btn.setMinimumHeight(40)
        self.add_btn.setStyleSheet(btn_style)
        self.make_btn.setStyleSheet(btn_style)
        self.link_btn.setStyleSheet(btn_style)
        self.add_btn.clicked.connect(self.setupAdd)
        self.make_btn.clicked.connect(self.setupMake)
        self.link_btn.clicked.connect(self.setupLink)
        self.account_list = QListWidget()
        sql_1 = """SELECT account_no FROM owns WHERE user_name='{}'""".format(self.username)
        cursor.execute(sql_1)
        accounts = [i[0] for i in cursor.fetchall()]
        for i in accounts:
            self.account_list.addItem(str(i))
        self.account_list.itemClicked.connect(self.selected)

        stylesheet = """
                    QWidget{
                        background-image: url("./assets/dollar_trans.png"); 
                        background-attachment: fixed;
                        background-repeat: no-repeat; 
                        background-position: center;
                    }
                """
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(stylesheet)
        self.outTab = QWidget()
        self.outTab.setObjectName("tabi")
        self.inTab = QWidget()
        self.inTab.setStyleSheet("tabo")
        self.tabs.addTab(self.outTab, "Expenditure")
        self.tabs.addTab(self.inTab, "Income")

        # filters
        self.yearText = QLineEdit()
        self.yearText.setPlaceholderText("Year")
        self.monthText = QLineEdit()
        self.monthText.setPlaceholderText("Month")
        self.dayText = QLineEdit()
        self.dayText.setPlaceholderText("Day")
        self.hourText = QLineEdit()
        self.hourText.setPlaceholderText("Hour")
        self.amountText = QLineEdit()
        self.amountText.setPlaceholderText("Amount no less than")

        self.yearText.returnPressed.connect(self.search)
        self.monthText.returnPressed.connect(self.search)
        self.dayText.returnPressed.connect(self.search)
        self.hourText.returnPressed.connect(self.search)
        self.amountText.returnPressed.connect(self.search)

        entries = QHBoxLayout()
        entries.addWidget(self.yearText)
        entries.addWidget(self.monthText)
        entries.addWidget(self.dayText)
        entries.addWidget(self.hourText)
        entries.addWidget(self.amountText)

        h_add = QHBoxLayout()
        h_add.addWidget(self.add_btn)
        h_add.addWidget(self.make_btn)
        h_add1=QHBoxLayout()
        h_add1.addWidget(self.link_btn)
        h_list = QHBoxLayout()
        h_list.addWidget(self.account_list)
        v_1 = QVBoxLayout()
        v_1.addLayout(h_add)
        v_1.addLayout(h_add1)
        v_1.addLayout(h_list)

        self.tab_info = QLabel("Account Information")
        self.tab_info.setFrameStyle(QFrame.StyledPanel)
        self.tab_info.setAlignment(Qt.AlignCenter)
        self.info_label = QLabel()
        self.info_label.setGeometry(1, 1, 1, 1)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setFrameStyle(QFrame.StyledPanel)
        self.info_label.setStyleSheet('font: 75 9pt "Arial";')
        self.tab_info.setStyleSheet('font: 87 20pt "Bodoni MT Black";')
        self.placeholderLabel=QLabel("Transaction Information")

        v_2 = QGridLayout()
        v_2.addWidget(self.tab_info, 0, 0, 2, -1)
        v_2.addWidget(self.info_label, 3, 0, 2, -1)
        v_2.addWidget(self.tabs, 6, 0, 10, -1)
        v_2.addLayout(entries, 17, 0, 1, -1)

        self.info_g = QGridLayout(self.centralwidget)
        self.info_g.addLayout(v_1, 0, 0, -1, 2)
        self.info_g.addLayout(v_2, 0, 2, -1, 6)
        self.MainWindow.setCentralWidget(self.centralwidget)

    def setupLink(self):
        self.linkPopup=LinkPopup(self.username)
        self.linkPopup.sigSend.connect(self.sendMail)

    def showHistory(self):
        sql_="select time from login where user_name='{}'".format(self.username)
        cursor.execute(sql_)
        result=cursor.fetchall()
        historyList=[i[0] for i in result]
        self.centralwidget=QWidget(self.MainWindow)
        self.historyScrollArea=QScrollArea()
        self.scrollWidget=QWidget()
        self.scrollWidget.setStyleSheet("background: transparent")
        self.scrollVbox=QVBoxLayout()
        self.historyScrollArea.setObjectName("scrollArea")
        stylesheet = """
            QWidget#scrollArea {
                background-image: url("./assets/time.png"); 
                background-attachment: fixed;
                background-repeat: no-repeat; 
                background-position: center;
            }
        """
        self.historyScrollArea.setStyleSheet(stylesheet)

        for i in historyList:
            object=QLabel(str(i))
            object.setStyleSheet("font: 75 10pt 'Arial'; background: transparent")
            self.scrollVbox.addWidget(object)

        self.scrollWidget.setLayout(self.scrollVbox)
        self.historyScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.historyScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.historyScrollArea.setWidgetResizable(True)
        self.historyScrollArea.setWidget(self.scrollWidget)
        self.MainWindow.setCentralWidget(self.historyScrollArea)

    def logout(self):
        self.MainWindow.close()
        os.execvp('python', ['python', __file__])

    def selected(self, item):
        sql_="""
        WITH  T AS (SELECT * FROM account WHERE account_no={})
        SELECT T.account_no, T.balance, AT.account_type, T.currency FROM T, account_types AT
        WHERE AT.type_id=T.type_id;
        """.format(int(item.text()))
        sql_1 = "select sent_amount, datetime, to_account from transaction where from_account={}".format(item.text())
        sql_2 = 'select received_amount, datetime, from_account from transaction where to_account={}'.format(item.text())

        cursor.execute(sql_)
        result=cursor.fetchall()

        account_no, balance, account_type, currency=result[0]

        self.info_label.setText("Your account with number {} is a {} account, with balance of {}{}".format(account_no, account_type, balance, currency))
        cursor.execute(sql_1)
        res_out=cursor.fetchall()
        cursor.execute(sql_2)
        res_in=cursor.fetchall()
        self.acc_info=(res_out, res_in)
        self.setTable(self.acc_info, 0)

    def setTable(self, hist_list, pageNo):
        hist_out, hist_in = hist_list
        logging.debug("Error 1")
        self.out_table = QTableWidget(len(hist_out), 3)
        self.in_table = QTableWidget(len(hist_in), 3)
        headersOut = ["Amount", "Time", "To"]
        headersIn = ["Amount", "Time", "From"]
        self.out_table.setHorizontalHeaderLabels(headersOut)
        self.in_table.setHorizontalHeaderLabels(headersIn)
        header = self.out_table.horizontalHeader()
        header1 = self.in_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header1.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header1.setSectionResizeMode(1, QHeaderView.Stretch)
        header1.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        for i, item in enumerate(hist_out):
            # logging.debug("Bug1")
            amount, time, to=item
            amountItem=QTableWidgetItem(str(amount))
            timeItem=QTableWidgetItem(str(time))
            toItem=QTableWidgetItem(str(to))
            self.out_table.setItem(i, 0, amountItem)
            self.out_table.setItem(i, 1, timeItem)
            self.out_table.setItem(i, 2, toItem)
        for i, item in enumerate(hist_in):
            # logging.debug("Bug2")
            amount, time, to=item
            amountItem=QTableWidgetItem(str(amount))
            timeItem=QTableWidgetItem(str(time))
            toItem=QTableWidgetItem(str(to))
            self.in_table.setItem(i, 0, amountItem)
            self.in_table.setItem(i, 1, timeItem)
            self.in_table.setItem(i, 2, toItem)

        self.tabs.removeTab(0)
        self.tabs.removeTab(0)
        self.outTab=QWidget()
        self.inTab=QWidget()
        self.tabs.addTab(self.outTab, "Expenditure")
        self.tabs.addTab(self.inTab, "Income")
        self.tabs.setCurrentIndex(pageNo)

        outV=QVBoxLayout()
        outV.addWidget(self.out_table)
        self.outTab.setLayout(outV)

        inV=QVBoxLayout()
        inV.addWidget(self.in_table)
        self.inTab.setLayout(inV)

    def search(self):
        year=self.yearText.text()
        month=self.monthText.text()
        day=self.dayText.text()
        hour=self.hourText.text()

        timeRe=""
        if year=='':
            timeRe+='....'
        else:
            timeRe+=year
        timeRe+='-'
        if month=='':
            timeRe+='..'
        else:
            timeRe+=month
        timeRe+='-'
        if day=='':
            timeRe+='..'
        else:
            timeRe+=day
        timeRe+=' '
        if hour=='':
            timeRe+='..:..:..'
        else:
            timeRe+=hour
            timeRe+=':..:..'

        amountText=self.amountText.text()
        amount=0
        try:
            amount=int(amountText)
        except ValueError:
            if amountText!='':
                self.amountText.setStyleSheet(error_style)
                self.amountText.clear()

        res = []
        logging.debug(timeRe)
        ind=self.tabs.currentIndex()
        toSearch = self.acc_info[ind]
        print("acc info 0=", toSearch)
        for i in toSearch:
            # print(str(i[1]))
            if re.search(timeRe, str(i[1])) and i[0]>amount:
                print(str(i[1]))
                res.append(i)
        print("res=",res)
        if ind==0:
            result=(res, self.acc_info[1])
        else:
            result=(self.acc_info[0], res)
        print("result=",result)
        print("result[0]=", result[0])
        self.setTable(result, ind)

    def setupAdd(self):
        self.addPopup=addPopup(self.username)
        self.addPopup.setGeometry(100, 100, 500, 300)
        self.addPopup.show()

    def setupMake(self):
        sql_="""select a.account_no, a.balance, a.currency, t.account_type
        from owns O, account A, account_types T 
        where o.account_no=a.account_no and 
        o.user_name='{}' and 
        t.type_id=a.type_id""".format(self.username)
        cursor.execute(sql_)
        result=cursor.fetchall()
        self.makePopup=makePopup(result, self.username)
        self.makePopup.setGeometry(100, 100, 500, 300)
        self.makePopup.sendSignal.connect(self.sendMail)
        self.makePopup.show()

    def refresh(self):
        self.showAccount()

    def sendMail(self, req):
        to = To(self.email)
        subject, content=req
        mail = Mail(from_email, to, subject, content)
        try:
            response=my_sg.send(mail)
        except Exception as e:
            print(e.message)

class LinkPopup(QWidget):
    sigSend=pyqtSignal(object)
    def __init__(self, username):
        super().__init__()
        self.username=username
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Linking to an account")
        self.setGeometry(100, 100, 350, 80)

        self.target = QLineEdit()
        self.target.setPlaceholderText("Account number to link.")
        self.confirmBtn=QPushButton("Confirm")
        self.confirmBtn.clicked.connect(self.verifyLink)
        self.confirmBtn.setStyleSheet(btn_style)

        v=QVBoxLayout()
        v.addWidget(self.target)
        v.addWidget(self.confirmBtn)
        v.setAlignment(Qt.AlignCenter)
        self.setLayout(v)
        self.show()

    def verifyLink(self):
        sql_="select * from account where account_no={}".format(self.target.text())
        sql_1="""select account_no from owns 
        where user_name='{}'""".format(self.username)
        cursor.execute(sql_)
        self.result=cursor.fetchall()
        if self.result==[]:
            self.target.clear()
            self.target.setPlaceholderText("Account doesn't exist.")
            self.target.setStyleSheet(error_style)
            return
        cursor.execute(sql_1)
        res_1 = cursor.fetchall()
        acc_list = [i[0] for i in res_1]
        if self.target.text() in acc_list:
            self.target.clear()
            self.target.setPlaceholderText("Account already owned by you")
            self.target.setStyleSheet(error_style)
            return
        self.passwordW=PasswordWidget(self.result[0][4])
        self.passwordW.passSignal.connect(self.makeLink)

    def makeLink(self):
        toLink=self.target.text()
        sql_ = "insert into owns (user_name, account_no) values ('{}', {})".format(self.username, toLink)
        sql_1 = """update account 
                set type_id=3
                where account_no={}""".format(toLink)
        cursor.execute(sql_)
        cursor.execute(sql_1)
        connection.commit()
        subject = "Link Successful"
        content = "This is to confirm that your linkage to {} is successful".format(toLink)
        self.sigSend.emit((subject, content))
        self.close()

class addPopup(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username=username
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Adding an account...")
        self.a_no_E = QLineEdit()
        # self.a_no_E.setAlignment(Qt.AlignHCenter)
        self.a_no_E.setStyleSheet(input_style)
        # self.a_no_E.setMinimumSize(250, 50)
        self.a_no_E.setMaxLength(330)
        self.a_no_E.setPlaceholderText("Account Number")
        self.a_no_T = QLabel()

        h_a_no_E = QHBoxLayout()
        h_a_no_E.setAlignment(Qt.AlignCenter)
        h_a_no_E.addWidget(self.a_no_E)
        h_a_no_E.addWidget(self.a_no_T)

        self.a_ps_E = QLineEdit()
        self.a_ps_E.setAlignment(Qt.AlignHCenter)
        self.a_ps_E.setStyleSheet(input_style)
        # self.a_ps_E.setMinimumSize(250, 50)
        self.a_ps_E.setMaxLength(330)
        self.a_ps_E.setEchoMode(QLineEdit.Password)
        self.a_ps_E.setPlaceholderText("Password")

        self.a_cfm_ps_E = QLineEdit()
        self.a_cfm_ps_E.setAlignment(Qt.AlignHCenter)
        self.a_cfm_ps_E.setStyleSheet(input_style)
        # self.a_cfm_ps_E.setMinimumSize(250, 50)
        self.a_cfm_ps_E.setMaxLength(330)
        self.a_cfm_ps_E.setEchoMode(QLineEdit.Password)
        self.a_cfm_ps_E.setPlaceholderText("Confirm Password")
        self.a_cfm_ps_T = QLabel()

        h_a_cfm_ps_H = QHBoxLayout()
        h_a_cfm_ps_H.setAlignment(Qt.AlignCenter)
        h_a_cfm_ps_H.addWidget(self.a_cfm_ps_E)
        h_a_cfm_ps_H.addWidget(self.a_cfm_ps_T)

        self.cur_cb = QComboBox()
        self.cur_cb.addItems(["---Select Currency---"])
        sql_="""select currency from currency"""
        cursor.execute(sql_)
        result=cursor.fetchall()
        self.currs=[i[0] for i in result]
        self.cur_cb.addItems(self.currs)

        self.type_cb = QComboBox()
        self.type_cb.addItems(["---Select Account Type---"])
        sql_1="""select * from account_types order by type_id"""
        cursor.execute(sql_1)
        result=cursor.fetchall()
        self.a_types=[i[1] for i in result]
        self.type_cb.addItems(self.a_types)

        self.cfm_btn = QPushButton("Confirm")
        self.cfm_btn.clicked.connect(self.addAccount)
        self.cfm_btn.setStyleSheet(btn_style)
        self.cfm_btn.setMinimumSize(50, 50)

        self.ccl_btn = QPushButton("Cancel")
        self.ccl_btn.clicked.connect(lambda: self.close())
        self.ccl_btn.setStyleSheet(btn_style)
        self.ccl_btn.setMinimumSize(50, 50)

        h_btn = QHBoxLayout()
        h_btn.addWidget(self.cfm_btn)
        h_btn.addWidget(self.ccl_btn)

        v = QVBoxLayout()
        v.addStretch()
        v.addLayout(h_a_no_E)
        v.addWidget(self.a_ps_E)
        v.addLayout(h_a_cfm_ps_H)
        v.addWidget(self.cur_cb)
        v.addWidget(self.type_cb)
        v.addLayout(h_btn)
        v.addStretch()
        logging.debug("Bug")
        self.setLayout(v)

    def addAccount(self):
        a=len(self.a_no_E.text())
        b=len(self.a_ps_E.text())
        if a==0 or b==0:
            if a==0:
                self.a_no_E.setStyleSheet(error_style)
            if b==0:
                self.a_no_E.setStyleSheet(error_style)
            return
        try:
            if len(self.a_no_E.text())>10:
                self.a_no_E.setStyleSheet(error_style)
                self.a_no_E.clear()
                self.a_no_E.setPlaceholderText("Account number too long (<10 digits)")
                # self.a_no_T.setText("Account number too long")
                # self.a_no_T.setStyleSheet("QLabel {font-color: red}")
                return
            acc_no=int(self.a_no_E.text())
        except ValueError as e:
            self.a_no_E.setStyleSheet(error_style)
            self.a_no_E.clear()
            self.a_no_E.setPlaceholderText("Account number must be digits")
            # self.a_no_T.setText("Account number must be digits")
            # self.a_no_T.setStyleSheet("QLabel {font-color: red}")
            return
        sql_0="""select account_no from account where account_no={}""".format(acc_no)
        cursor.execute(sql_0)
        res_0=cursor.fetchall()
        if(res_0)!=[]:
            self.a_no_T.setText("Account already exists")
            self.a_no_T.setStyleSheet("QLabel {color: red}")
            return
        if self.a_ps_E.text()!=self.a_cfm_ps_E.text():
            self.a_cfm_ps_E.clear()
            self.a_cfm_ps_E.setPlaceholderText("Passwords don't match")
            self.a_ps_E.setStyleSheet(error_style)
            self.a_ps_E.setStyleSheet(error_style)
            return
        if self.cur_cb.currentIndex()==0 or self.type_cb.currentIndex()==0:
            if self.cur_cb.currentIndex()==0:
                self.cur_cb.setStyleSheet('QComboBox {border: 1px solid #fc0000}')
            else:
                self.type_cb.setStyleSheet('QComboBox {border: 1px solid #fc0000}')
            return

        sql_1="""INSERT INTO account (account_no, balance, type_id, currency, password) 
        VALUES ({},{},{},'{}','{}')""".format(acc_no, 0, self.type_cb.currentIndex(), self.cur_cb.currentText(), self.a_ps_E.text())
        sql_2="""INSERT INTO owns (user_name, account_no) VALUES('{}', {})""".format(self.username, acc_no)
        cursor.execute(sql_1)
        cursor.execute(sql_2)
        connection.commit()
        self.close()

class makePopup(QWidget):
    sendSignal=pyqtSignal(object)
    def __init__(self, accs, username):
        super().__init__()
        self.accs=accs
        self.username=username
        self.frequentlist=[]
        if os.path.exists('frequentlist.pickle'):
            with open('frequentlist.pickle') as f:
                self.frequentlist=pickle.load(f)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Making a transaction")

        self.from_label=QLabel("From account:")
        self.to_label=QLabel("To account:")
        self.amount_label=QLabel("Amount:")
        self.currency_label=QLabel()

        self.select_from=QComboBox()

        self.select_from.currentTextChanged.connect(lambda:
                                                    self.currency_label.setText(self.accs[self.select_from.currentIndex()][2]))
        for i in self.accs:
            self.select_from.addItem(str(i[0])+' ('+str(i[1])+i[2]+') '+i[3])
        self.select_to=QComboBox()
        self.select_to.setEditable(True)
        self.select_to.setPlaceholderText("Select or specify an account")
        self.text_amount=QLineEdit()

        sql_="""
        with accs as
        (select account_no from owns 
        where user_name='{}'),
        to_accs as 
        (select distinct to_account from 
        transaction, accs
        where from_account=accs.account_no),
        acc_curr as (select account_no, currency from
        to_accs, account
        where to_account=account_no)
        select name, O.account_no, currency from
        customer C, acc_curr AC, owns O
        where O.user_name = C.user_name and
        O.account_no =  AC.account_no
        """.format(self.username)
        cursor.execute(sql_)
        self.result=cursor.fetchall()
        for i in self.result:
            name, account_no, currency=i
            self.select_to.addItem(str(account_no)+' ('+currency+') '+" "+name)
        self.confirm_btn=QPushButton("Confirm")
        self.confirm_btn.setMinimumHeight(40)
        self.confirm_btn.setStyleSheet(btn_style)
        self.confirm_btn.clicked.connect(self.verifyTransaction)
        self.cancel_btn=QPushButton("Cancel")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setStyleSheet(btn_style)
        self.cancel_btn.clicked.connect(lambda: self.close())

        h1=QHBoxLayout()
        h1.addWidget(self.from_label)
        h1.addWidget(self.select_from)

        h2=QHBoxLayout()
        h2.addWidget(self.to_label)
        h2.addWidget(self.select_to)

        h3=QHBoxLayout()
        h3.addWidget(self.confirm_btn)
        h3.addWidget(self.cancel_btn)
        h3.setAlignment(Qt.AlignCenter)

        h4=QHBoxLayout()
        h4.addWidget(self.amount_label)
        h4.addWidget(self.text_amount)
        h4.addWidget(self.currency_label)
        h4.setAlignment(Qt.AlignCenter)

        v=QVBoxLayout()
        v.addStretch()
        v.addLayout(h1)
        v.addLayout(h2)
        v.addLayout(h4)
        v.addLayout(h3)

        v.addStretch()

        self.setLayout(v)

    def checkPassword(self):
        self.from_account=self.accs[self.select_from.currentIndex()][0]
        sql_="select password from account where account_no={}".format(self.from_account)
        cursor.execute(sql_)
        result=cursor.fetchall()
        self.passwordWidget=PasswordWidget(result[0][0])
        self.passwordWidget.passSignal.connect(self.makeTransaction)

    def verifyTransaction(self, passed):
        self.from_account=self.accs[self.select_from.currentIndex()][0]
        self.balance=self.accs[self.select_from.currentIndex()][1]

        try:
            self.to_account = int(self.select_to.currentText())
        except ValueError as e:
            idx=self.select_to.currentIndex()
            if idx==-1:
                self.select_to.setStyleSheet(error_style_c)
                return
            else:
                self.to_account=self.result[idx][1]
        self.currency=self.accs[self.select_from.currentIndex()][2]
        sql_="select * from account where account_no={}".format(self.to_account)
        cursor.execute(sql_)
        result=cursor.fetchall()
        if result==[]:
            self.select_to.setStyleSheet(error_style)
            self.select_to.clear()
            self.select_to.setPlaceholderText("Account doesn't exist")

        elif self.balance<int(self.text_amount.text()):
            self.text_amount.setStyleSheet(error_style)
            self.currency_label.setText(self.currency_label.text()+"Not enough balance")
        else:
            self.amount=int(self.text_amount.text())
            self.checkPassword()

    def makeTransaction(self):
        sql_3 = "select * from account where account_no={}".format(self.to_account)
        cursor.execute(sql_3)
        result = cursor.fetchall()
        recipient_currency=result[0][3]
        if recipient_currency==self.currency:
            recipient_amount=self.amount
        else:
            sql_4 = "select value from currency where currency='{}'".format(recipient_currency)
            cursor.execute(sql_4)
            value_res=cursor.fetchall()
            sql_5="select value from currency where currency='{}'".format(self.currency)
            cursor.execute(sql_5)
            value_self=cursor.fetchall()
            reci_value=value_res[0][0]
            self_value=value_self[0][0]
            recipient_amount=round(self.amount*self_value/reci_value,2)
        sql_ = "update account set balance=balance-{} where account_no={}".format(self.amount, self.from_account)
        sql_1 = "update account set balance=balance+{} where account_no={}".format(recipient_amount, self.to_account)
        sql_2 = """insert into transaction (sent_amount, received_amount, datetime, from_account, to_account) 
                    values ({}, {}, '{}', {}, {})""".format(
            self.amount,
            recipient_amount,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            self.from_account,
            self.to_account
        )
        cursor.execute(sql_)
        cursor.execute(sql_1)
        cursor.execute(sql_2)
        connection.commit()

        subject = "Successful Transaction!"
        text_content="""This email is to confirm your transaction 
        of {}{} from {} to {} is successful.""".format(self.amount, self.currency, self.from_account, self.to_account)
        if self.currency != recipient_currency:
            text_content+=" ({}{} received by the other account.)".format(recipient_amount, recipient_currency)
        content = Content("text/plain", text_content)
        self.sendSignal.emit((subject, content))
        self.close()

class PasswordWidget(QWidget):
    passSignal=pyqtSignal(object)
    def __init__(self, passwd):
        super().__init__()
        self.passwd=passwd
        self.setupUI()

    def setupUI(self):
        self.password_label=QLabel("Password: ")
        self.setWindowTitle("Entering password")
        self.setGeometry(100, 100, 600, 150)
        self.password_text=QLineEdit()
        self.password_text.setEchoMode(QLineEdit.Password)
        self.password_text.setPlaceholderText("Please enter the password for this account")
        self.password_text.returnPressed.connect(self.confirmClicked)
        self.confirm_btn=QPushButton("Confirm")
        self.confirm_btn.setStyleSheet(btn_style)
        self.confirm_btn.clicked.connect(self.confirmClicked)
        h_1=QHBoxLayout()
        h_1.addWidget(self.password_label)
        h_1.addWidget(self.password_text)
        h_1.setAlignment(Qt.AlignCenter)
        h_2=QHBoxLayout()
        h_2.addWidget(self.confirm_btn)
        h_2.setAlignment(Qt.AlignCenter)
        v=QVBoxLayout()
        v.addLayout(h_1)
        v.addLayout(h_2)
        self.setLayout(v)
        self.show()

    def confirmClicked(self):
        input=self.password_text.text()
        if input==self.passwd:
            self.confirm_btn.setDisabled(True)
            self.password_text.setDisabled(True)
            self.passSignal.emit(True)
            self.success = QWidget()
            self.success.setGeometry(100, 100, 50, 50)
            self.success.setWindowTitle("Success")
            self.success.successLabel = QLabel("Success!")
            self.success.okButton = QPushButton("OK")

            self.success.okButton.clicked.connect(lambda: [self.close(), self.success.close()])
            self.success.okButton.setStyleSheet(btn_style)
            v = QVBoxLayout()
            v.setAlignment(Qt.AlignCenter)
            v.addWidget(self.success.successLabel)
            v.addWidget(self.success.okButton)
            self.success.setLayout(v)
            self.success.show()
        else:
            self.warning = QWidget()
            self.warning.setGeometry(100, 100, 50, 50)
            self.warning.setWindowTitle("Error")
            self.warning.warningLabel = QLabel("Incorrect Password")
            self.warning.okButton = QPushButton("OK")
            self.warning.okButton.setStyleSheet(btn_style)
            self.warning.okButton.clicked.connect(lambda: self.warning.close())
            l = QVBoxLayout()
            l.setAlignment(Qt.AlignCenter)
            l.addWidget(self.warning.warningLabel)
            l.addWidget(self.warning.okButton)
            self.warning.setLayout(l)
            self.warning.show()
            return

class UILoginWindow(object):
    def __init__(self, MainWindow):
        self.MainWindow=MainWindow

    def setupUI(self):
        self.MainWindow.setWindowTitle("IKYC Login Wizard")
        self.centralwidget = QWidget(self.MainWindow)

        self.hkulogo = QLabel()
        self.hkulogo.setGeometry(1, 1, 1, 1)
        self.hkulogo.setAlignment(Qt.AlignCenter)
        self.hkulogo.setFrameStyle(QFrame.StyledPanel)
        self.hkulogo.setPixmap(QPixmap("assets/hkulogo.png"))
        self.hkulogo_t = QLabel("Welcome to HKU iKYC System")
        self.hkulogo_t.setAlignment(Qt.AlignCenter)
        self.hkulogo_t.setFrameStyle(QFrame.StyledPanel)

        # the username input frame
        self.input_style = 'QLineEdit {border: 1px solid #c8c8c8; font-family: ubuntu, arial; font-size: 14px;}'
        self.error_style = 'QLineEdit {border: 1px solid #fc0000; font-family: ubuntu, arial; font-size: 14px;}'
        self.username = QLineEdit()
        self.username.setMinimumSize(250, 30)
        self.username.setStyleSheet(self.input_style)
        self.username.setPlaceholderText('username')

        # the preferred name input frame
        self.name = QLineEdit()
        self.name.setMinimumSize(250, 30)
        self.name.setStyleSheet(self.input_style)
        self.name.setPlaceholderText('preferred name')

        # the email input
        self.email = QLineEdit()
        self.email.setMinimumSize(250, 30)
        self.email.setStyleSheet(self.input_style)
        self.email.setPlaceholderText('email')

        # login or signup buttons
        self.btn_login = QPushButton('Login')
        self.btn_login.clicked.connect(self.loginClicked)
        self.btn_login.setMinimumHeight(40)
        self.btn_login.setStyleSheet(btn_style)
        self.btn_signup = QPushButton('Signup')
        self.btn_signup.clicked.connect(self.signupClicked)
        self.btn_signup.setMinimumHeight(40)
        self.btn_signup.setStyleSheet(btn_style)

        # the camera feed of the app
        self.cam_feed = QLabel()
        self.cam_feed.setMinimumSize(640, 480)
        self.cam_feed.setAlignment(Qt.AlignCenter)
        self.cam_feed.setFrameStyle(QFrame.StyledPanel)
        self.cam_feed.setStyleSheet('QLabel {background-color: #000000;}')

        # for signup and login button
        h_box_signup_login = QHBoxLayout()
        h_box_signup_login.addWidget(self.btn_signup)
        h_box_signup_login.addWidget(self.btn_login)

        # the return button
        self.rtn=QPushButton("Return")
        self.rtn.clicked.connect(self.returnMain)
        self.rtn.setStyleSheet(btn_style)
        self.rtn.setFixedSize(60, 30)

        # the left panel
        self.v_box1 = QVBoxLayout()
        self.v_box1.addStretch()
        self.v_box1.addWidget(self.hkulogo)
        self.v_box1.addWidget(self.hkulogo_t)
        self.v_box1.addLayout(h_box_signup_login)
        self.v_box1.addStretch()
        # the right camera feed panel
        v_box2 = QVBoxLayout()
        v_box2.addWidget(self.cam_feed)
        self.g_box0 = QGridLayout(self.centralwidget)
        self.g_box0.addLayout(self.v_box1, 0, 0, -1, 2)
        self.g_box0.addLayout(v_box2, 0, 2, -1, 4)

        self.MainWindow.updateSig.connect(self.update)
        self.MainWindow.setCentralWidget(self.centralwidget)
    def signupClicked(self):
        while self.v_box1.itemAt(3).count():
            item=self.v_box1.itemAt(3).takeAt(0)
            widget=item.widget()
            if widget is not None:
                widget.setParent(None)
        self.v_box1.removeItem(self.v_box1.itemAt(4))
        self.v_box1.addWidget(self.username)
        self.v_box1.addWidget(self.name)
        self.v_box1.addWidget(self.email)
        self.v_box1.addWidget(self.rtn)
        self.v_box1.addStretch()
        self.username.returnPressed.connect(self.signupEntered)
        self.name.returnPressed.connect(self.signupEntered)
        self.email.returnPressed.connect(self.signupEntered)


    def loginClicked(self):
        while self.v_box1.itemAt(3).count():
            item=self.v_box1.itemAt(3).takeAt(0)
            widget=item.widget()
            if widget is not None:
                widget.setParent(None)
        self.v_box1.removeItem(self.v_box1.itemAt(4))
        # self.v_box1.addWidget(self.username)
        # self.v_box1.addWidget(self.rtn)
        self.v_box1.addStretch()
        self.loginEntered()
        # self.username.returnPressed.connect(self.loginEntered)
        # print(self.v_box1.count())

    def returnMain(self):
        while self.v_box1.count()>3:
            item=self.v_box1.takeAt(3)
            widget=item.widget()
            if widget is not None:
                widget.setParent(None)
        h_box_signup_login = QHBoxLayout()
        h_box_signup_login.addWidget(self.btn_signup)
        h_box_signup_login.addWidget(self.btn_login)
        self.v_box1.addLayout(h_box_signup_login)
        self.v_box1.addStretch()

    def update(self):
        # logging.debug("Oops")
        Qframe = QImage(self.MainWindow.registerer.display,
                        self.MainWindow.registerer.display.shape[1],
                        self.MainWindow.registerer.display.shape[0],
                        self.MainWindow.registerer.display.strides[0],
                        QImage.Format_RGB888)
        self.cam_feed.setPixmap(QPixmap.fromImage(Qframe))

    def loginEntered(self):
        self.t_login=threading.Thread(target=lambda: self.MainWindow.registerer.login(), daemon=True)
        self.t_login.start()

    def signupEntered(self):
        username=self.username.text()
        pref_name=self.name.text()
        email=self.email.text()
        if username=='':
            self.username.setStyleSheet(self.error_style)
            return
        if pref_name=='':
            self.name.setStyleSheet(self.error_style)
            return
        if email=='':
            self.email.setStyleSheet(self.error_style)
            return
        response=requests.get("https://isitarealemail.com/api/email/validate",
            params = {'email': email})
        status=response.json()['status']
        if status!="valid":
            self.email.setStyleSheet(self.error_style)
            self.email.clear()
            self.email.setPlaceholderText("Invalid Email")
            return
        self.t_signup=threading.Thread(target=lambda: self.MainWindow.registerer.signup(username, pref_name, email), daemon=True)
        self.t_signup.start()

class MainWindow(QMainWindow):
    updateSig=pyqtSignal(object)
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setStyleSheet('QWidget {background-color: #ffffff;}')
        self.setWindowIcon(QIcon('assets/hkulogo.png'))
        self.uiLoginWindow = UILoginWindow(self)
        self.uiUserWindow=UIInfoTab(self)
        self.uiInfoTab = UIInfoTab(self)
        self.registerer=Registerer(self)
        self.registerer.logged_in_sig.connect(self.startUIUserWindow)
        self.registerer.frameMadeSig.connect(self.notifyUpdate)
        self.registerer.work()
        self.startUILoginWindow()

    def notifyUpdate(self, img):
        self.updateSig.emit(img)

    def startUIUserWindow(self, username):
        self.registerer.cam.release()
        self.uiUserWindow.setupUI(username)
        self.show()

    def startUIInfoTab(self,username):
        self.registerer.t_registerer.join()
        self.registerer.deleteLater()
        self.uiInfoTab.setupUI(username)
        self.show()

    def startUILoginWindow(self):
        self.uiLoginWindow.setupUI()
        self.show()

class Registerer(QObject):
    logged_in_sig = pyqtSignal(object)
    frameMadeSig=pyqtSignal(object)
    def __init__(self, MainWindow):
        super(Registerer, self).__init__()
        self.MainWindow=MainWindow
        self.engine=pyttsx3.init()
        self.engine.setProperty('rate', 175)
        self.cam=cv2.VideoCapture(0)
        self.logged_in_sig.connect
        self.flg_signing_up=False
        self.flg_logging_in=False
        self.flg_logged_in=False
        self.display = None

    def work(self):
        self.t_registerer=threading.Thread(target=self.normal_display, daemon=True)
        self.t_registerer.start()

    def signup(self, username, pref_name, email):
        self.flg_signing_up=True
        featurelist=[]
        userlist = []
        if os.path.exists('featurelist.pickle'):
            with open('featurelist.pickle', 'rb') as f:
                featurelist=pickle.load(f)
        if os.path.exists('userlist.pickle'):
            with open('userlist.pickle', 'rb') as f:
                userlist=pickle.load(f)

        if username in userlist:
            self.engine.say("Username already exists")
            self.engine.runAndWait()
            logging.debug("Username in list")
            return

        while True:
            _, res=self.cam.read()
            gray=cv2.cvtColor(res, cv2.COLOR_RGB2GRAY)
            faces=face_cascade.detectMultiScale(gray, scaleFactor=1.5, minNeighbors=3)
            if type(faces)==np.ndarray:
                enc=face_recognition.face_encodings(res)[0]
                if featurelist!=[]:
                    result=face_recognition.compare_faces(featurelist, enc)
                    dists=face_recognition.face_distance(featurelist, enc)
                    if result[np.argmin(dists)]:
                        self.engine.say("Face already registered")
                        self.engine.runAndWait()
                        return
                featurelist.append(enc)
                userlist.append(username)
                logging.debug("Appended")
                with open('userlist.pickle', 'wb') as handle:
                    pickle.dump(userlist, handle)
                with open('featurelist.pickle', 'wb') as handle:
                    pickle.dump(featurelist, handle)
                logging.debug("Registered")
                self.engine.say(("Hello", pref_name, "thank you for choosing the IKYC system! You may log in now"))
                self.engine.runAndWait()
                sql_="""insert into customer (user_name, name, registration_date, email)
                values ('{}', '{}', '{}', '{}')""".format(username, pref_name, date.today().strftime("%Y-%m-%d"), email)
                cursor.execute(sql_)
                connection.commit()
                break
        return

    def login(self):
        with open('userlist.pickle', 'rb') as f:
            userlist = pickle.load(f)
        with open('featurelist.pickle', 'rb') as f:
            featurelist=pickle.load(f)
        while True:
            _, res = self.cam.read()
            logging.debug("Bug1")
            encodings=face_recognition.face_encodings(res)
            if len(encodings)!=0:
                foi=encodings[0]
                results=face_recognition.compare_faces(featurelist, foi)
                dists=face_recognition.face_distance(featurelist, foi)
                poi=np.argmin(dists)
                if not results[poi]:
                    self.engine.say("Face not recognized")
                    self.engine.runAndWait()
                else:

                    self.flg_logged_in=True
                    sql_ = "SELECT registration_date, name FROM customer WHERE user_name='{}'".format(userlist[poi])
                    sql_1="""insert into login (user_name, time) values ('{}', '{}')""".format(userlist[poi], datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    cursor.execute(sql_)
                    result = cursor.fetchall()
                    self.engine.say(("Hello, {}, welcome to the iKYC system, thank you for your {} days here".format(
                        result[0][1], (date.today() - result[0][0]).days)))
                    cursor.execute(sql_1)
                    connection.commit()
                    self.logged_in_sig.emit(userlist[poi])
                    self.engine.runAndWait()
                    break
        return

    def normal_display(self):
        while not self.flg_logged_in:
            # only pure video stream displayed
            _, res = self.cam.read()
            frame = cv2.cvtColor(res, cv2.COLOR_BGR2RGB)
            # logging.debug("Normal frame created")
            self.display = frame[:, ::-1, :].copy()
            self.frameMadeSig.emit(True)
        return

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    sys.exit(app.exec_())


