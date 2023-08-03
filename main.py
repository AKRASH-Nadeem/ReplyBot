from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtSql import QSqlDatabase, QSqlQuery, QSqlTableModel,QSqlRelationalDelegate
from MainWindow import Ui_MainWindow
# Custom Dialogs and Widgets
from custom_widget import Labels_Widget
from add_dialog import Ui_Dialog
from Test_dialog import Ui_Test_dialog
# import resources
import resources_rc
# utility module
import re
# Multithreading imports
from Process_handling import Test_Bot,AIogramBot

def verify_telegram_bot_token(token):
    pattern = r'^\d+:[A-Za-z0-9_-]+$'
    return bool(re.match(pattern, token))


def setup_database():
    try:
        # Create a SQLite database
        db = QSqlDatabase.addDatabase('QSQLITE')
        db.setDatabaseName('information.db')

        # Open the database
        if not db.open():
            print("Error: Could not open the database.")
            return False

        message_table = """
        CREATE TABLE IF NOT EXISTS "messages" (
        "id"	INTEGER NOT NULL UNIQUE,
        "message"	TEXT NOT NULL,
        "incomming_message"	TEXT,
        "regex"	TEXT,
        "casesensitive"	INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY("id"))"""

        bot_token = """
        CREATE TABLE IF NOT EXISTS "bot_token" (
        "id"	INTEGER NOT NULL UNIQUE,
        "token"	TEXT NOT NULL,
        PRIMARY KEY("id"))"""

        # Create a table if it doesn't exist
        query = QSqlQuery()
        query.exec(message_table)
        query.exec(bot_token)
        db.commit()
        db.close()
        return db
    except Exception as error:
        sys.exit(1)


class Add_Dialog(QtWidgets.QDialog):
    updated = QtCore.pyqtSignal()
    def __init__(self,db,id=None):
        super().__init__()
        self.db = db
        self.id = id
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.dialog_save_btn.clicked.connect(self.save_func)
        self.ui.dialog_cancel_btn.clicked.connect(self.close_func)
        self.ui.incomming_message_text.textChanged.connect(self.disable_regex)
        self.ui.regex_text.textChanged.connect(self.disable_incomming_text)
    def disable_regex(self,text):
        if text != "" and text != None:
            self.ui.regex_text.clear()
            self.ui.regex_text.setDisabled(True)
        else:
            self.ui.regex_text.setDisabled(False)
    def disable_incomming_text(self,text):
        if text != "" and text != None:
            self.ui.incomming_message_text.clear()
            self.ui.incomming_message_text.setDisabled(True)
        else:
            self.ui.incomming_message_text.setDisabled(False)
    def close_func(self):
        print("closing...")
        self.close()
    def save_func(self):
        regex = self.ui.regex_text.text()
        incomming_message = self.ui.incomming_message_text.text()
        case_sensitive = int(self.ui.case_sensitive_checkbox.isChecked())
        message = self.ui.replymessage_textarea.toPlainText()
        if (regex != "" or incomming_message != "") and case_sensitive != None and (message != "" and message != None):
            self.db.open()
            query = QSqlQuery(self.db)
            if self.id != None:
                query.prepare("UPDATE messages SET incomming_message=:inc, regex=:reg,message=:mess,casesensitive=:case WHERE id=:id")
                query.bindValue(":inc",incomming_message)
                query.bindValue(":reg",regex)
                query.bindValue(":mess",message)
                query.bindValue(":case",case_sensitive)
                query.bindValue(":id",self.id)
            else:
                query.prepare("INSERT OR IGNORE INTO messages(incomming_message,regex,message,casesensitive) VALUES(:inc,:reg,:mess,:case)")
                query.bindValue(":inc",incomming_message)
                query.bindValue(":reg",regex)
                query.bindValue(":mess",message)
                query.bindValue(":case",case_sensitive)
            query.exec()
            self.db.commit()
            self.db.close()
            self.close()
            self.updated.emit()
        else:
            self.ui.error.setText("Please fill the above fields to add it")
            return

class MainWindow(QtWidgets.QMainWindow):
    bot_started = QtCore.pyqtSignal(bool)
    minimized_to_tray = QtCore.pyqtSignal()
    tray_error = QtCore.pyqtSignal(str)
    def __init__(self):
        super().__init__()

        # Set up the UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowIcon(QtGui.QIcon(":/logo/images/logo.png"))
        self.thread_list = []
        self.thread_pool = QtCore.QThreadPool()
        self.bot_thread = None
        self.ui.add_btn.clicked.connect(self.open_dialog)
        self.ui.test_btn.clicked.connect(self.test_bot_token)
        self.ui.start_btn.clicked.connect(self.bot_starter_funtion)
        self.ui.stop_btn.setEnabled(False)
        self.ui.stop_btn.clicked.connect(self.stop_bot)
        self.db = setup_database()
        self.model = QSqlTableModel()
        dataquery = QSqlQuery()
        dataquery.exec_("SELECT token FROM bot_token ORDER BY token DESC")
        token = None
        if dataquery.next():
            token = dataquery.value(0)
        else:
            print(dataquery.lastError().text())
        if token:
            self.ui.token_input.setText(token)
        else:
            pass
        query = QSqlQuery()
        self.data_query = "SELECT id,incomming_message,regex,message,casesensitive FROM messages"
        query.prepare(self.data_query)
        if query.exec_():
            self.model.setQuery(query)
        else:
            self.statusBar().showMessage("Error : "+str(query.lastError().text()))
        self.ui.tableView.setModel(self.model)
        self.ui.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.tableView.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.ui.tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.tableView.doubleClicked.connect(self.edit_dialog)
        self.ui.delete_btn.clicked.connect(self.delete_row)
        self.ui.clear_all_btn.clicked.connect(self.clear_all)
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        window_x = (screen.width() - self.width()) // 2
        window_y = (screen.height() - self.height()) // 2
        self.move(window_x, window_y)
    def error_message(self,message):
        if self.isVisible():
            dialog = QtWidgets.QDialog()
            ui = Ui_Test_dialog()
            ui.setupUi(dialog)
            ui.label.setText("Error")
            ui.status_label.setText(message)
            ui.save_btn.setText("Ok")
            ui.save_btn.clicked.connect(dialog.close)
            dialog.setWindowTitle("Error Message")
            dialog.exec_()
        else:
            self.tray_error.emit(message)
    def bot_starter_funtion(self):
        
        if not self.bot_thread:
            try:
                self.bot_thread = AIogramBot(self.ui.token_input.text(),self.bot_started)
                self.bot_thread.started.connect(self.bot_message)
                self.bot_thread.stopped.connect(self.bot_message)
                self.bot_thread.error.connect(self.error_message)
                self.bot_thread.setTerminationEnabled(True)
                self.bot_thread.start()
                self.ui.start_btn.setEnabled(False)
            except Exception as error:
                print("Error 1 :",error)
                self.error_message(str(error))
                return
            
            # self.ui.stop_btn.setEnabled(True)
            # self.bot_thread.message_received.connect(self.print_message)
    def stop_bot(self):
        print("is thread running ",self.bot_thread.isRunning())
        if self.bot_thread.isRunning():
            self.bot_thread.stop_bot()
            # self.ui.start_btn.setEnabled(False)
            self.ui.stop_btn.setEnabled(False)
            self.bot_thread = None
    def bot_message(self,Stopped=False):
        
        if Stopped:
            self.ui.statusbar.showMessage("Bot stopped",5000)
            # self.ui.stop_btn.setEnabled(False)
            self.ui.start_btn.setEnabled(True)
        else:
            self.ui.statusbar.showMessage("Bot started...")
            self.ui.statusbar.showMessage("Bot Running...")
            # self.ui.start_btn.setEnabled(False)
            self.ui.stop_btn.setEnabled(True)
    def clear_all(self):
        self.db.open()
        query = QSqlQuery()
        query.prepare("DELETE FROM messages")
        if query.exec_():
            self.ui.statusbar.showMessage("Cleared all messages auto reply data",10000)
        else:
            self.ui.statusbar.showMessage(query.lastError().text)
        self.db.close()
        self.update_model()
    def delete_row(self):
        selectedrows = self.ui.tableView.selectionModel().selectedRows()
        for item in selectedrows:
            row = item.row()
            model = self.ui.tableView.model()
            index = model.index(row,0)
            id = model.data(index)
            self.db.open()
            query = QSqlQuery()
            query.prepare("DELETE FROM messages WHERE id=:rowid")
            query.bindValue(":rowid",id)
            if query.exec_():
                self.ui.statusbar.showMessage("Message deleted ",5000)
            else:
                self.ui.statusbar.showMessage("Error : "+str(query.lastError().text()))
        self.db.close()
        self.update_model()
    def update_model(self):
        # self.model.layoutChanged.emit()
        self.db.open()
        query = QSqlQuery()
        query.prepare(self.data_query)
        if query.exec_():
            self.model.setQuery(query)
        else:
            self.statusBar().showMessage("Error : "+str(query.lastError().text()))
        self.db.close()
    def edit_dialog(self,index):
        row = index.row()
        id = self.model.record(row).value("id")
        edit_dialog = Add_Dialog(self.db,id=id)
        casesensitive = self.model.record(row).value("casesensitive")
        message = self.model.record(row).value("message")
        regex = self.model.record(row).value("regex")
        incomming_message = self.model.record(row).value("incomming_message")
        edit_dialog.ui.incomming_message_text.setText(incomming_message)
        edit_dialog.ui.regex_text.setText(regex)
        edit_dialog.ui.replymessage_textarea.setPlainText(message)
        edit_dialog.ui.case_sensitive_checkbox.setChecked(False if casesensitive == 0 else True)
        edit_dialog.updated.connect(self.update_model)
        edit_dialog.exec_()
        # edit_dialog.ui.incomming_message_text.setText(incomming_message)
        # print(message)

    def test_bot_token(self):
        token = self.ui.token_input.text()
        if verify_telegram_bot_token(token):
            worker = Test_Bot(token)
            worker.status.connect(self.Connection_status_dialog)
            worker.finished.connect(self.thread_finished)
            worker.started.connect(self.thread_started)
            self.thread_list.append(worker)
            worker.start()
        else:
            dialog = QtWidgets.QDialog()
            ui = Ui_Test_dialog()
            ui.setupUi(dialog)
            ui.status_label.setText("The Token format is not correct please insert Correct Token")
            dialog.exec_()

        print(token)
    def thread_started(self):
        self.ui.statusbar.showMessage("Testing...")
    def thread_finished(self):
        self.ui.statusbar.showMessage("Testing Done!",5000)
    def savetoken(self,dialog):
        token = self.ui.token_input.text()
        self.db.open()
        query = QSqlQuery(self.db)

        # Prepare the SQL command to insert 
        query.prepare("INSERT OR IGNORE INTO bot_token (token) VALUES (:token)")
        query.bindValue(":token",token)
        query.exec()
        self.db.commit()
        self.db.close()
        dialog.close()

    def Connection_status_dialog(self,mydict):
        if mydict['status'] == True:
            dialog = QtWidgets.QDialog()
            ui = Ui_Test_dialog()
            ui.setupUi(dialog)
            ui.save_btn.clicked.connect(lambda : self.savetoken(dialog))
            for key in mydict.keys():
                if key == "status":
                    ui.status_label.setText("Active")
                    continue
                widget = Labels_Widget(str(key)+" : ",mydict[key])
                ui.status_widget.layout().addWidget(widget)
            dialog.exec_()
        elif mydict['status'] == False:
            dialog = QtWidgets.QDialog()
            ui = Ui_Test_dialog()
            ui.setupUi(dialog)
            ui.status_label.setText(mydict['message'])
            dialog.exec_()
        else:
            dialog = QtWidgets.QDialog()
            ui = Ui_Test_dialog()
            ui.setupUi(dialog)
            ui.status_label.setText("Unexpected Error contact developer")
            dialog.exec_()
    def open_dialog(self):
        print("in here")
        dialog = Add_Dialog(self.db)
        dialog.updated.connect(self.update_model)
        dialog.exec_()
    def closeEvent(self,event):
        event.ignore()  # Ignore the close event to keep the window running
        self.hide()
        self.minimized_to_tray.emit()

        



class MyApplication(QtWidgets.QApplication):
    def __init__(self,*argv):
        super().__init__(*argv)
        self.icon = QtGui.QIcon(":/logo/images/logo.png")
        # Adding item on the menu bar
        self.tray = QtWidgets.QSystemTrayIcon()
        self.tray.setIcon(self.icon)
        self.tray.setVisible(True)
        # Creating the options
        self.menu = QtWidgets.QMenu()
        self.start_opt = QtWidgets.QAction("start bot")
        self.stop_opt = QtWidgets.QAction("stop bot")
        self.stop_opt.setDisabled(True)
        self.menu.addAction(self.start_opt)
        self.menu.addAction(self.stop_opt)
        
        # To quit the app
        self.quit_option = QtWidgets.QAction("Quit")
        self.quit_option.triggered.connect(self.quit)
        self.menu.addAction(self.quit_option)
        
        # Adding options to the System Tray
        self.tray.setContextMenu(self.menu)
    def button_visibility(self,started=False):
        if started:
            self.start_opt.setDisabled(True)
            self.stop_opt.setDisabled(False)
            self.tray.showMessage("Telegram bot","The bot is started",QtWidgets.QSystemTrayIcon.MessageIcon.Information,3000)
        else:
            self.stop_opt.setDisabled(True)
            self.start_opt.setDisabled(False)
            self.tray.showMessage("Telegram bot","The bot is stopped",QtWidgets.QSystemTrayIcon.MessageIcon.Information,3000)
            
    def minimized_to_tray_message(self):
        self.tray.showMessage("Telegram bot","Software is minimized to system tray",QtWidgets.QSystemTrayIcon.MessageIcon.Information,3000)

    def systemtray_triggered(self,reason,windows):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            windows.show()
        else:
            return
    def error_message(self,message):
        self.tray.showMessage("Telegram bot",message,QtWidgets.QSystemTrayIcon.MessageIcon.Critical,5000)

if __name__ == "__main__":
    import sys
    app = MyApplication(sys.argv)
    windows = MainWindow()
    app.start_opt.triggered.connect(windows.bot_starter_funtion)
    app.stop_opt.triggered.connect(windows.stop_bot)
    app.tray.activated.connect(lambda reason: app.systemtray_triggered(reason,windows))
    windows.minimized_to_tray.connect(app.minimized_to_tray_message)
    windows.bot_started.connect(app.button_visibility)
    windows.tray_error.connect(app.error_message)
    windows.show()
    sys.exit(app.exec_())
