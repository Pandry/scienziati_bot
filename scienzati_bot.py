import telebot
#pip3 install PyTelegramBotAPI
import time
import sqlite3
import random
import re
import sys

#Settings class

class Settings:
	TelegramApiKey = "676490981:AAELlmTlQLD4_1HojhzWIX4yISDrVU5qDmA"
	SupremeAdmins = ["pandry","andreaidini"]#Lowercase username!
	ITGroup = -1001068546876
	OTGroup = -1001218814107
	subscriptionRows = 7


###
## Bot Inizialization
###

#Create the bot instance
bot = telebot.TeleBot(Settings.TelegramApiKey)
botInfo = bot.get_me()
print("Authorized on @" + botInfo.username)


###
## Database Inizialization
###

#Initialize the database connection 
dbConnection = sqlite3.connect('database.sqlitedb', check_same_thread=False)

#Set the resulting array to be associative
# https://stackoverflow.com/a/2526294
dbConnection.row_factory = sqlite3.Row

#Sets the database cursor.
#It is used to submit queires to the DB and manage it
# https://docs.python.org/2/library/sqlite3.html
dbC = dbConnection.cursor()
# Remember to close the connection at the end of the program with conn.close()

#This part of the code is used to initalize the database.
#It runs the "seed" query
#This is the query that is used to initialize the SQLite3 database

#TODO: add referencing message to make the bot statful
initQuery= """CREATE TABLE IF NOT EXISTS `Users` (
`ID`  INTEGER NOT NULL UNIQUE,
`Nickname`  TEXT NOT NULL,
`Biography`  TEXT,
`Status`  INTEGER NOT NULL DEFAULT 0,
`Permissions`  INTEGER DEFAULT 0,
`ITMessageNumber`  INTEGER DEFAULT 0,
`OTMessageNumber`  INTEGER DEFAULT 0,
`LastSeen`  TEXT DEFAULT '0000-00-00 00:00:00',
PRIMARY KEY(`ID`)
);

CREATE TABLE IF NOT EXISTS `Lists` (
`ID`  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
`Name`  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS `Subscriptions` (
`ID`  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
`List`  INTEGER NOT NULL,
`User`  INTEGER NOT NULL,
FOREIGN KEY(`User`) REFERENCES `Users`(`ID`),
FOREIGN KEY(`List`) REFERENCES `Lists`(`ID`)
);"""
# Seeds the databse - Executes the inital query
#I use executescript instead of excut to permit to do multiple queries
dbC.executescript(initQuery)
# Save (commit) the changes
dbConnection.commit()





###
# Constant message values
###

class constResources:

	intro_mex = """Ciao 😁
Sei confuso? 
Questo è il bot del gruppo @scienza e permette di usufruire di queste funzioni:
/iscriviti per iscriverti al database di utenti e per partecipare alle liste sugli interessi
/aderisci per iscriverti ad una lista, puoi usare anche: /partecipa, /registrati e /sottoscrivi
/bio per scrivere qualcosa su di te
/liste per scoprire le liste già presenti
/gdpr consulta le norme sul GDPR
/privs elenca i privilegi utente
/disiscrivi per cancellarti da una lista alla quale hai aderito, puoi usare pure: /esci, /rimuovi, /iscrizioni e /aderenze"""

	admin_help = """Comandi admin... blabla
	/nuovalista
	/rimuovilista
	/del delete bot message
	=== CA$TA THINGS ===
	/setadmin
	/unsetadmin
	/grantlist
	/revokelist
	"""

	version = "α0.1.2.6"
	
	gdpr_message = "Raccogliamo il numero di messaggi, nickname, ID e ultima volta che l'utente ha scritto. Per richiedere l'eliminazione dei propri dati contattare un amministratore ed uscire dal gruppo"



###
# Constant values
#  Those values are static and are used to represent the user's state/permission
#  The Permission funtion are used to execute bitwise operations, and the status are simply used to compare the statuses
###

# Status legend
# -2 - Waiting for biograhy
# -1 - User just created - needs to insert bio
# 0 - User created
# 15 - Banned


class UserStatus: #Enum emulator
	WAITING_FOR_LIST = -5
	WAITING_FOR_BIOGRAPHY = -2
	USER_JUST_CREATED = -1
	ACTIVE = 0
	BANNED = 15

	#Dummy functions - Those functions are "dummy": they are just used to compare a given input to the value in the class
	def IsWaitingForBio(status):
		if status == UserStatus.WAITING_FOR_BIOGRAPHY:
			return True
		return False

	def IsWaitingForListName(status):
		if status == UserStatus.WAITING_FOR_LIST:
			return True
		return False

	def IsJustCreated(status):
		if status == UserStatus.USER_JUST_CREATED:
			return True
		return False

	def IsActive(status):
		if status == UserStatus.ACTIVE:
			return True
		return False

	def IsBanned(status):
		if status == UserStatus.BANNED:
			return True
		return False

	# Complex functions
	#CanEnterBio Is used whern checking if a user has privileges to edit its Biography
	def CanEnterBio(status):
		if status == UserStatus.BANNED:
			return False 
		return True



# Permissions legend
#
# xxx0 - Admin flag - 1 = admin
# xx0x - Channed flag - 1 = can post to channel
# x0xx -  flag - 1 = can post to channel
#
class UserPermission: #Siply do an AND with the permission
	ADMIN=int('1', 2)
	CAN_ADD_ADMIN=int('10', 2)
	CAN_REMOVE_ADMIN=int('100', 2)
	CHANNEL=int('1000', 2)
	LIST=int('10000', 2)

	def IsAdmin(permission):
		if (permission & UserPermission.ADMIN) == UserPermission.ADMIN:
			return True
		return False
	
	def SetAdminPermission(permission):
		return permission | UserPermission.ADMIN
	
	def RemoveAdminPermission(permission):
		return permission & (not(UserPermission.ADMIN))

	def CanAddAdmin(permission):
		if (permission & UserPermission.CAN_ADD_ADMIN) == UserPermission.CAN_ADD_ADMIN:
			return True
		return False
	
	def SetCanAddAdmin(permission):
		return permission | UserPermission.CAN_ADD_ADMIN
	
	def RemoveCanAddAdmin(permission):
		return permission & (not(UserPermission.CAN_ADD_ADMIN))

	def CanRemoveAdmin(permission):
		if (permission & UserPermission.CAN_REMOVE_ADMIN) == UserPermission.CAN_REMOVE_ADMIN:
			return True
		return False
	
	def SetCanRemoveAdmin(permission):
		return permission | UserPermission.CAN_REMOVE_ADMIN
	
	def RemoveCanRemoveAdmin(permission):
		return permission & (not(UserPermission.CAN_REMOVE_ADMIN))
	
	def CanForwardToChannel(permission):
		if (permission & UserPermission.CHANNEL) == UserPermission.CHANNEL:
			return True
		return False
	
	def SetForwardToChannel(permission):
		return permission | UserPermission.CHANNEL
	
	def RemoveForwardToChannel(permission):
		return permission & (not(UserPermission.CHANNEL))
	
	def ListPermission(permission):
		if (permission & UserPermission.LIST) == UserPermission.LIST:
			return True
		return False

	def SetListPermission(permission):
		return permission | UserPermission.LIST
	
	def RemoveListPermission(permission):
		return permission & (not(UserPermission.LIST))
	
	


###
# Helper functions
#  Those functions will be used as support functions for the bot. 
#  Those function are "database wrappers"
###

#GetUser is used to return the row corresponding to the user in the database.
#It went introduced because the same query repeted over and over
def GetUser(userID):
		#Create a database cursor
	dbC = dbConnection.cursor()
	#Selects the users
	dbC.execute('SELECT * FROM Users WHERE ID=?', (userID,))
	#Fetch the results
	rows = dbC.fetchall()
	#Check if the users exists
	if len(rows) > 0:
		if len(rows) > 1:
			#something's wrong here, the ID shouln't be greater than one
			raise Exception('The user exceed 1. Something could be wrong with the database. Code error #S658')
		else:
			#The users exists, returns the permission
			return rows[0]
	else:
		#No record found - ID could be erroneous
		#TODO: Throw error?
		return False

#UpdateBio is a helper function to update the biography of a user.
#It returns true in case of success, otherwise it returns false
def UpdateBio(userdID, bio):
	dbC = dbConnection.cursor()
	res = dbC.execute('INSERT INTO Users (ID, Nickname, Status) VALUES (?,?,?)', (userdID, bio, UserStatus.USER_JUST_CREATED,) )
	if res:
		CommitDb()
		return True
	return False

# GetUserPermissionsValue takes the userID as input and returns the permission value (int) direclty from the database
def GetUserPermissionsValue(userID):
	user = GetUser(userID)
	if user != False:
		return user["Permissions"]
	#No user exist, returning Flase for now
	return False

# GetUserPermissionsValue takes the userID as input and returns the permission value (int) direclty from the database
def SetUserPermissionsValue(userID,newPermission):
	dbC = dbConnection.cursor()
	res = dbC.execute('UPDATE Users SET Permissions=? WHERE ID = ?', (newPermission, userID,) )
	if res:
		CommitDb()
		return True
	return False

def GetUserStatusValue(userID):
	user = GetUser(userID)
	if user != False:
		return user["Status"]
	#No user exist, returning Flase for now
	return False

#IncrITGroupMessagesCount increments the number of messages in the IT group
def IncrITGroupMessagesCount(userID):
	dbC = dbConnection.cursor()
	res = dbC.execute('UPDATE Users SET ITMessageNumber = ITMessageNumber + 1 WHERE ID = ?', (userID,) )
	if res:
		CommitDb()
		return True
	return False

#IncrOTGroupMessagesCount increments the number of messages in the OT group
def IncrOTGroupMessagesCount(userID):
	dbC = dbConnection.cursor()
	res = dbC.execute('UPDATE Users SET OTMessageNumber = OTMessageNumber + 1 WHERE ID = ?', (userID,) )
	if res:
		CommitDb()
		return True
	return False

def UpdateLastSeen(userID, date):
	dbC = dbConnection.cursor()
	res = dbC.execute('UPDATE Users SET LastSeen=? WHERE ID = ?', (date, userID,) )
	if res:
		CommitDb()
		return True
	return False

def CommitDb():
	dbConnection.commit()

def GetUserNickname(userID):
	dbC = dbConnection.cursor()
	dbC.execute('SELECT `Nickname` FROM Users WHERE `ID`=?;', (userID,))
	res = dbC.fetchone()
	if res != None:
		return res[0]
	return False

#CreateNewListWithoutDesc creates a new list :O
def CreateNewList(name):
	dbC = dbConnection.cursor()
	try:
		res = dbC.execute('INSERT INTO Lists (Name) VALUES (?)', (name,) )
		if res:
			CommitDb()
			return True
		return False
	except:
		return False

def GetLists(limit = Settings.subscriptionRows-1, offset=0):
	dbC = dbConnection.cursor()
	if limit == None:
		dbC.execute('SELECT * FROM Lists')
	else:
		dbC.execute('SELECT * FROM Lists LIMIT ? OFFSET ?', (limit, offset,))
	res = dbC.fetchall()
	if len(res) >0:
		return res
	return False 


def GetListsNames(limit = Settings.subscriptionRows-1, offset=0):
	dbC = dbConnection.cursor()
	if limit == None:
		dbC.execute('SELECT `Name` FROM Lists')
	else:
		dbC.execute('SELECT `Name` FROM Lists LIMIT ? OFFSET ?', (limit, offset,))
	return dbC.fetchall()

def SubscribeUserToList(userID, listID):
	#If user is not in the list
	dbC = dbConnection.cursor()
	dbC.execute('SELECT * FROM Subscriptions WHERE User=? AND List=?', (userID, listID))
	res = dbC.fetchall()
	if len(res) >0:
		#User already subscribed
		return False
	#Create subscription
	dbC = dbConnection.cursor()
	dbC.execute('INSERT INTO Subscriptions (User, List) VALUES (?,?)', (userID, listID))
	res = dbC.fetchall()
	if res != None:
		CommitDb()
		return True
	return False

def UnubscribeUserFromList(userID, listID):
	#If user is not in the list
	dbC = dbConnection.cursor()
	dbC.execute('DELETE FROM Subscriptions WHERE User=? AND List=?', (userID, listID))
	res = dbC.fetchall()
	if res != None:
		CommitDb()
		return True
	return False
	
def AvailableListsToUser(userID, limit=Settings.subscriptionRows-1, offset=0):
	#If user is not in the list
	dbC = dbConnection.cursor()
	if limit == None:
		dbC.execute('SELECT ID, Name FROM Lists WHERE Lists.ID NOT IN (SELECT List FROM Subscriptions WHERE User=?)')
	else:
		dbC.execute('SELECT ID, Name FROM Lists WHERE Lists.ID NOT IN (SELECT List FROM Subscriptions WHERE User=?) LIMIT ? OFFSET ?', (userID, limit,offset))
	res = dbC.fetchall()
	if len(res) >0:
		#User already subscribed
		return res
	return False


def SubscribedLists(userID, limit=Settings.subscriptionRows-1, offset=0):
	#If user is not in the list
	dbC = dbConnection.cursor()
	if limit == None:
		dbC.execute('SELECT Lists.ID, Lists.Name FROM Lists INNER JOIN Subscriptions ON Subscriptions.List = Lists.ID WHERE Subscriptions.User=?', (userID,))
	else:
		dbC.execute('SELECT Lists.ID, Lists.Name FROM Lists INNER JOIN Subscriptions ON Subscriptions.List = Lists.ID WHERE Subscriptions.User=? LIMIT ? OFFSET ?', (userID, limit,offset))
	res = dbC.fetchall()
	if len(res) >0:
		#User already subscribed
		return res
	return False

def GetListID(listName):
	dbC = dbConnection.cursor()
	dbC.execute('SELECT `ID` FROM Lists WHERE `Name`=?;', [listName])
	res = dbC.fetchone()
	if res != None:
		return res[0]
	return False

def GetListName(listID):
	dbC = dbConnection.cursor()
	dbC.execute('SELECT `Name` FROM Lists WHERE `ID`=?;', (listID,))
	res = dbC.fetchone()
	if res != None:
		return res[0]
	return False
	
def ListExists(listName):
	dbC = dbConnection.cursor()
	dbC.execute('SELECT `ID` FROM Lists WHERE `Name`=?', (listName,))
	res = dbC.fetchall()
	if len(res) >0:
		#User already subscribed
		return True
	return False

def GetListSubscribers(listID):
	dbC = dbConnection.cursor()
	dbC.execute('SELECT `User` FROM Subscriptions WHERE `List`=?', (listID,))
	res = dbC.fetchall()
	if len(res) >0:
		#User already subscribed
		return res
	return False

def DeleteList(listID):
	#If user is not in the list
	dbC = dbConnection.cursor()
	res =dbC.execute('DELETE FROM Lists WHERE ID=?', (listID,))
	if res != None:
		CommitDb()
		return True
	return False

def UpdateNickname(userID, nickname):
	dbC = dbConnection.cursor()
	res = dbC.execute('UPDATE Users SET Nickname=? WHERE ID = ?', (nickname.lower().replace('@',''), userID, ))
	if res:
		CommitDb()
		return True
	return False

#Abort the inserting process of a new Bio
#WARNING: CHECK IF USER IS BANNED BEFORE, OR HE WILL GET UNBANNED
def abortNewBio(userID):
	dbC = dbConnection.cursor()
	res = dbC.execute('UPDATE Users SET Status=? WHERE ID = ?', (UserStatus.ACTIVE, userID,) )
	if res:
		CommitDb()
		return True
	return False

def GetUserBio(userID):
	dbC = dbConnection.cursor()
	dbC.execute('SELECT `Biography` FROM Users WHERE `ID`=?;', (userID,))
	res = dbC.fetchone()
	if res != None:
		return res[0]
	return False

def abortNewList(userID):
	dbC = dbConnection.cursor()
	res = dbC.execute('UPDATE Users SET Status=? WHERE ID = ?', (UserStatus.ACTIVE, userID,) )
	if res:
		CommitDb()
		return True
	return False

def getUsersIdLike(userNick):
	dbC = dbConnection.cursor()
	dbC.execute('SELECT `ID` FROM Users WHERE `Nickname` LIKE ?;', ("%"+userNick.replace("%", ":%")+"%",))
	res = dbC.fetchall()
	if res != None:
		return res
	return False

def getUserId(userNick):
	userNick = userNick.replace('@','').lower()
	dbC = dbConnection.cursor()
	dbC.execute('SELECT `ID` FROM Users WHERE `Nickname`= ?;', (userNick,))
	res = dbC.fetchone()
	if res != None:
		return res[0]
	return False

def setNewUserStatus(userdID, statusID):
	dbC = dbConnection.cursor()
	#res = dbC.execute('UPDATE Users SET Status=? WHERE ID = ?;', (UserStatus.WAITING_FOR_BIOGRAPHY , message.from_user.id,) )
	res = dbC.execute('UPDATE Users SET Status=? WHERE ID = ?', (statusID , userdID,) )
	if res:
		CommitDb()
		return True
	return False


def IsUserSuperadmin(userNick):
	return userNick.lower() in Settings.SupremeAdmins


def getUserPermissionText(userid):
	userPermission = GetUserPermissionsValue(userid)
	msg = "Ecco i privilegi dell'utente @" + GetUserNickname(userid) + ":\n ⚙️ Ranks\nSupreme admin: "
	if IsUserSuperadmin(GetUserNickname(userid)):
		msg = msg + "✅ Sì"
	else:
		msg = msg + "❌ Nope"
	msg = msg + "\n"

	msg = msg + "Admin: "
	if UserPermission.IsAdmin(userPermission):
		msg = msg + "✅ Sì"
	else:
		msg = msg + "❌ Nope"
	msg = msg + "\n"

	msg = msg + "\n📝Privileges\n"
	msg = msg +  "Gestione liste: "
	if UserPermission.ListPermission(userPermission):
		msg = msg + "✅ Sì"
	else:
		msg = msg + "❌ Nope"
	msg = msg + "\n"

	msg = msg + "Aggiunta amministratori: "
	if UserPermission.CanAddAdmin(userPermission):
		msg = msg + "✅ Sì"
	else:
		msg = msg + "❌ Nope"
	msg = msg + "\n"

	msg = msg + "Eliminazione amministratori: "
	if UserPermission.CanRemoveAdmin(userPermission):
		msg = msg + "✅ Sì"
	else:
		msg = msg + "❌ Nope"
	msg = msg + "\n"

	msg = msg + "Inoltro al canale: "
	if UserPermission.CanForwardToChannel(userPermission):
		msg = msg + "✅ Sì"
	else:
		msg = msg + "❌ Nope"
	return msg

###
# Bot functions
###

#Start command.
# This is the function called when the bot is started or the help commands are sent
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
	markup = telebot.types.InlineKeyboardMarkup()
	markup.row(telebot.types.InlineKeyboardButton("❌ Chiudi", callback_data="deleteDis"))
	bot.reply_to(message, constResources.intro_mex, reply_markup=markup)

@bot.message_handler(commands=['adminhelp'])
def send_admhelp(message):
	markup = telebot.types.InlineKeyboardMarkup()
	markup.row(telebot.types.InlineKeyboardButton("❌ Chiudi", callback_data="deleteDis"))
	bot.reply_to(message, constResources.admin_help, reply_markup=markup)

@bot.message_handler(commands=['v', 'version'])
def send_version(message):
	markup = telebot.types.InlineKeyboardMarkup()
	markup.row(telebot.types.InlineKeyboardButton("❌ Chiudi", callback_data="deleteDis"))
	bot.reply_to(message,  "V: " + constResources.version, reply_markup=markup)

# Replies with the static message before
@bot.message_handler(commands=['privs'])
def send_privs(message):
	args = message.text.split(' ')
	userid = message.from_user.id
	markup = telebot.types.InlineKeyboardMarkup()
	markup.row(telebot.types.InlineKeyboardButton("❌ Chiudi", callback_data="deleteDis"))

	if len(args) == 2:
		reqUserid = getUserId(args[1])
		if reqUserid != False:
			userid = reqUserid
		else:
			bot.reply_to(message, "L'utente inserito non è stato trovato in database", reply_markup=markup)
	elif len(args) > 2:
		bot.reply_to(message, "Sono stati inseriti troppi parametri", reply_markup=markup)
	
	if GetUser(userid) == False:
		bot.reply_to(message, "Non sei presente in database, perciò non è possibile conoscere il tuo livello di privilegi.", reply_markup=markup)
		return
	
	bot.reply_to(message,  getUserPermissionText(userid), reply_markup=markup)

# Replies with the static message before
@bot.message_handler(commands=['gdpr'])
def send_gdrp(message):
	bot.reply_to(message, constResources.gdpr_message)

### Messaggio di Iscrizione 
@bot.message_handler(commands=['iscrivi'])
def start_user_registration(message):
	if not message.from_user.is_bot and message.text != "" :
		# Tries to see 
		dbC = dbConnection.cursor()
		dbC.execute('SELECT * FROM Users WHERE ID=?', (message.from_user.id,))
		rows = dbC.fetchall()

		#if database.get(str(message.from_user.id),None) is None:
		if len(rows) > 0:
			#The user exists in database
			bot.reply_to(message, "Sei già registrato in database. se desideri modificare la tua biografia puoi farlo mediante il comando /bio")
		else:
			#The user needs to be created
			#bot.reply_to(message, "creazione nuovo record utente...")
			#Insert 
			dbC = dbConnection.cursor()
			res = dbC.execute('INSERT INTO Users (ID, Nickname, Status) VALUES (?,?,?)', (message.from_user.id, message.from_user.username, UserStatus.USER_JUST_CREATED,) )
			dbConnection.commit()
			if res:
				msg = bot.reply_to(message, "Congratulazioni, ti sei registrato correttamente! Ora puoi procedere ad inserire la tua biografia attraverso il comando /bio")
			else:
				msg = bot.reply_to(message, "Errore nella creazione del record")

		# this is to define step-by-step subscription
		#bot.register_next_step_handler(msg, first_registration)


### Aggioramento/ impostaizone bio
@bot.message_handler(commands=['bio', 'setbio'])
def setBio(message):
	if not message.from_user.is_bot and message.text != "" :
		# Gets info about the user
		user = GetUser(message.from_user.id)
		#Check if the user exists
		if user == False:
			#the user does not exist
			msg = bot.reply_to(message, "Non sei ancora registrato. Puoi registrarti attraverso il comando /iscrivi ")
		#Check its status
		else:
			#There's only one user, as it's supposed to be
			#Check if the user needs to set a biography
			if UserStatus.CanEnterBio(user["Status"]):
				res = setNewUserStatus(message.from_user.id, UserStatus.WAITING_FOR_BIOGRAPHY)
				#Tries to force the user to reply to the message
				#markup = telebot.types.ForceReply(selective=False)
				markup = telebot.types.InlineKeyboardMarkup()
				markup.row_width = 1
				markup.add(telebot.types.InlineKeyboardButton('❌ Annulla', callback_data=f"aBio"))
				currentBioMsg = GetUserBio(message.from_user.id)
				if currentBioMsg != None and currentBioMsg != "":
					currentBioMsg = "La tua attuale biografia è \"" + currentBioMsg + "\".\n"
				else:
					currentBioMsg = ""
				msg = bot.reply_to(message, currentBioMsg + "Per impostare una nuova biografia, scrivimela in chat privata o rispondendomi", reply_markup=markup)
				dbConnection.commit()
			else:
				#Nothing to do here
				msg = bot.reply_to(message, "You can't enter a bio.")


#Creazione di una nuova lista
@bot.message_handler(commands=['newlist', 'nuovalista'])
def newList(message):
	if IsUserSuperadmin(message.from_user.username) or UserPermission.IsAdmin(GetUserPermissionsValue(message.from_user.id)) or UserPermission.ListPermission(GetUserPermissionsValue(message.from_user.id)):
		if not message.from_user.is_bot and message.text != "" :
			# Gets info about the user
			user = GetUser(message.from_user.id)
			#Check if the user exists
			if user == False:
				#the user does not exist
				bot.reply_to(message, "Something's wrong here. error code: #Q534")
			else:
				res = setNewUserStatus(message.from_user.id,UserStatus.WAITING_FOR_LIST )
				markup = telebot.types.InlineKeyboardMarkup()
				markup.row_width = 1
				markup.add(telebot.types.InlineKeyboardButton('❌ Annulla', callback_data=f"aList"))
				msg = bot.reply_to(message, "Per creare una nuova lista, scrivi il nome in chat privata o in un messaggio che mi risponda rispondendomi", reply_markup=markup)
				dbConnection.commit()
	else:
		bot.reply_to(message, "Error 403 - ❌ Unauthorized")

#Creazione di una nuova lista
@bot.message_handler(commands=['deletelist', 'removelist', 'rimuovilista', 'eliminalista'])
def deleteListHandler(message):
	if IsUserSuperadmin(message.from_user.username) or UserPermission.IsAdmin(GetUserPermissionsValue(message.from_user.id)) or UserPermission.ListPermission(GetUserPermissionsValue(message.from_user.id)):
		if not message.from_user.is_bot and message.text != "" :
			# Gets info about the user
			user = GetUser(message.from_user.id)
			#Check if the user exists
			if user == False:
				#the user does not exist
				msg = bot.reply_to(message, "Something's wrong here. error code: #J258")
			else:
				#Asks for the bio
				#need to send message with a list
				liste = GetLists()
				markup = telebot.types.InlineKeyboardMarkup()
				#Print the lists as inline buttons
				msg = "Random message padding"
				if liste == False:#TODO test
					msg = "Al momento non è presente nessuna lista.\nSi prega di riprovare in seguito."
				else:
					
					for ulist in liste:
						markup.row(telebot.types.InlineKeyboardButton(ulist["Name"], callback_data="rlist-"+str(ulist["ID"])))
					rightbutton = telebot.types.InlineKeyboardButton(" ", callback_data="ignore")
					if AvailableListsToUser(message.from_user.id, limit=1, offset=int(Settings.subscriptionRows-1)) != False:
						rightbutton = telebot.types.InlineKeyboardButton(f"➡️", callback_data=f"orlist-"+str(Settings.subscriptionRows-1))
					markup.row(telebot.types.InlineKeyboardButton("❌ Chiudi", callback_data="deleteDis"), rightbutton)
						#⬅️ ➡️ 
				msg = bot.reply_to(message, msg, reply_markup=markup)
				#SubscribeUserToList()
				
	else:
		msg = bot.reply_to(message, "Error 403 - ❌ Unauthorized")

@bot.message_handler(commands=['del', 'delete'])
def deleteBotMessage(message):
	userPerm = GetUserPermissionsValue(message.from_user.id)
	if userPerm != False and (IsUserSuperadmin(message.from_user.username) or UserPermission.IsAdmin(userPerm)):
		if message.reply_to_message != None and message.reply_to_message.from_user.id == botInfo.id:
			bot.delete_message(message.chat.id , message.reply_to_message.message_id)


#Lista delle liste
@bot.message_handler(commands=['lists', 'liste'])
def showLists(message):
	markup = telebot.types.InlineKeyboardMarkup()
	markup.row(telebot.types.InlineKeyboardButton("❌ Chiudi", callback_data="deleteDis"))
	liste = GetListsNames(limit=None)
	msg = "Al momento esistono " + str(len(liste))+ " liste; eccole qui:\n"
	for list in liste:
		msg = msg + list[0] + "\n"
	if len(liste) == 0:
		msg = "Al momento non sono presenti liste"
	bot.reply_to(message, msg, reply_markup=markup)

@bot.message_handler(commands=['subscribe', 'join', 'registrati', 'partecipa', 'aderisci', 'sottoscrivi'])
def subscribeUserListHandler(message):
	user = GetUser(message.from_user.id)
	if user != False:
		#The user is registred in DB
		userStatus = GetUserStatusValue(message.from_user.id)
		if UserStatus.IsActive(userStatus):
			#Add to list
			msg = "Ecco un elenco delle liste attualmente disponibili:\n(Per sottoscriverti ad una lista, è sufficiente \"tapparla\")"
			#Get available lists
			lists = AvailableListsToUser(message.from_user.id)
			markup = telebot.types.InlineKeyboardMarkup()
			#Print the lists as inline buttons
			if lists == False:
				msg = "Al momento non è presente nessuna lista.\nSi prega di riprovare in seguito."
			else:
				for ulist in lists:
					#																			sub-{id} => subscript to list {id}
					markup.row(telebot.types.InlineKeyboardButton(ulist["Name"], callback_data="sub-"+str(ulist["ID"])))
				#If there are still lists, print the page delimiter
				#if len(lists) > Settings.subscriptionRows-1:
				if AvailableListsToUser(message.from_user.id, limit=1, offset=int(Settings.subscriptionRows-1)) != False:
					#																																	  osub-{n} => offest subscription, needed for pagination, 
					#Teels the offset to set to correctly display the pages
					markup.row(telebot.types.InlineKeyboardButton("❌ Chiudi", callback_data="deleteDis"), telebot.types.InlineKeyboardButton(f"➡️", callback_data=f"osub-"+str(Settings.subscriptionRows-1)))
					#⬅️ ➡️ 
			msg = bot.reply_to(message, msg, reply_markup=markup)
			#SubscribeUserToList()

		elif UserStatus.IsBanned(userStatus):
			#banned, not much you can do right now
			bot.reply_to(message, "Error 403 - ❌ Unauthorized")
		else:
			#User in another activity (like creating list)
			bot.reply_to(message, "Sembra che tu sia occupato in un'altra azione (come impostare una biografia).\n Sarebbe opportuno terminare quell'azione prima di cercare di intraprenderne altre")
	else:
		bot.reply_to(message, "Sarebbe opportuno registrarsi prima, tu non credi?\nPuoi farlo attraverso il comando /iscrivi")

@bot.message_handler(commands=['subscribedto', 'joinedto', 'inscriptions', 'iscrizioni','disiscrivi', 'disiscriviti', 'rimuovi', 'esci'])
def unsubscribeUserListHandler(message):
	user = GetUser(message.from_user.id)
	if user != False:
		#The user is registred in DB
		userStatus = GetUserStatusValue(message.from_user.id)
		if UserStatus.IsActive(userStatus):
			#Add to list
			msg = "Ecco un elenco delle liste alle quali sei attualmente iscritto:\n(Per rimuovere la sottoscrizione, è sufficiente \"tapparla\" e confermare)"
			#Get available lists
			lists = SubscribedLists(message.from_user.id)
			markup = telebot.types.InlineKeyboardMarkup()
			#Print the lists as inline buttons
			if lists == False:
				msg="Al momento non sei iscritto a nessuna lista.\nPuoi iscriverti ad una lista attraverso il comando /registrati."
			else:
				for ulist in lists:
					#																			sub-{id} => unsubscribe to list {id}
					markup.row(telebot.types.InlineKeyboardButton(ulist["Name"], callback_data="usub-"+str(ulist["ID"])))
				#If there are still lists, print the page delimiter
				#if len(lists) > Settings.subscriptionRows-1:
				if SubscribedLists(message.from_user.id, limit=1, offset=int(Settings.subscriptionRows-1)) != False:
					#																																	  osub-{n} => offest subscription, needed for pagination, 
					#Teels the offset to set to correctly display the pages
					#markup.row(telebot.types.InlineKeyboardButton(" ", callback_data="ignore"), telebot.types.InlineKeyboardButton(f"➡️", callback_data=f"ousub-"+str(Settings.subscriptionRows-1)))
					markup.row(telebot.types.InlineKeyboardButton("❌ Chiudi", callback_data="deleteDis"), telebot.types.InlineKeyboardButton(f"➡️", callback_data=f"ousub-"+str(Settings.subscriptionRows-1)))
					#⬅️ ➡️ 
			msg = bot.reply_to(message, msg, reply_markup=markup)
			#SubscribeUserToList()

		elif UserStatus.IsBanned(userStatus):
			#banned, not much you can do right now
			bot.reply_to(message, "Error 403 - ❌ Unauthorized")
		else:
			#User in another activity (like creating list)
			bot.reply_to(message, "Sembra che tu sia occupato in un'altra azione (come impostare una biografia).\n Sarebbe opportuno terminare quell'azione prima di cercare di intraprenderne altre")
	else:
		bot.reply_to(message, "Sarebbe opportuno registrarsi prima, tu non credi?\nPuoi farlo attraverso il comando /iscrivi")


@bot.message_handler(commands=['setadmin'])
def setAdminPermissionHandler(message):
	user = GetUser(message.from_user.id)
	if user != False:
		userPermission = GetUserPermissionsValue(message.from_user.id)
		if IsUserSuperadmin(message.from_user.username) or (UserPermission.IsAdmin(userPermission) and UserPermission.CanAddAdmin(userPermission)):
			args = message.text.split(' ')
			if len(args) == 2:
				newAdminNickname = args[1].replace('@','').lower()
				newAdminId = getUserId(newAdminNickname)
				if newAdminId == False:
					#It looks like there's no user called this way
					bot.reply_to(message, "❌ Sembra che l'utente non sia registrato.\nÈ opportuno farlo registrare prima di promuoverlo ad amministratore!")
					return
				newAdminpermission = GetUserPermissionsValue(newAdminId)
				newAdminpermission = UserPermission.SetAdminPermission(newAdminpermission)
				res = SetUserPermissionsValue(newAdminId, newAdminpermission)
				if res == True:
					#Say OK
					bot.reply_to(message, "✅ Admin impostato con successo!\nLode al nuovo admin, @" + newAdminNickname + "!")
				else:
					#not ok
					bot.reply_to(message, "❌ Impossibile impostare l'amministratore!")
				return
			else:
				bot.reply_to(message, "❌ Utilizzo: /setadmin {@}username")
				return
	bot.reply_to(message, "❌ Error 403 - Unauthorized")

@bot.message_handler(commands=['unsetadmin', 'removeadmin'])
def unsetAdminPermissionHandler(message):
	user = GetUser(message.from_user.id)
	if user != False:
		userPermission = GetUserPermissionsValue(message.from_user.id)
		if IsUserSuperadmin(message.from_user.username) or (UserPermission.IsAdmin(userPermission) and UserPermission.CanRemoveAdmin(userPermission)):
			args = message.text.split(' ')
			if len(args) == 2:
				oldAdminNickname = args[1].replace('@','').lower()
				oldAdminId = getUserId(oldAdminNickname)
				if oldAdminId == False:
					#It looks like there's no user called this way
					bot.reply_to(message, "❌ Sembra che l'utente non sia registrato.\nÈ opportuno farlo registrare prima di promuoverlo ad amministratore!")
					return
				oldAdminpermission = GetUserPermissionsValue(oldAdminId)
				if not UserPermission.IsAdmin(oldAdminpermission):
					bot.reply_to(message, "❌ Sembra che l'utente non sia amministratore!")
					return
				oldAdminpermission = UserPermission.RemoveAdminPermission(oldAdminpermission)
				res = SetUserPermissionsValue(oldAdminId, oldAdminpermission)
				if res == True:
					#Say OK
					bot.reply_to(message, "✅ Admin congedato con successo!")
				else:
					#not ok
					bot.reply_to(message, "❌ Impossibile congedare l'amministratore!")
				return
			else:
				bot.reply_to(message, "❌ Utilizzo: /removeadmin {@}username")
				return
	bot.reply_to(message, "❌ Error 403 - Unauthorized")


@bot.message_handler(commands=['grantlist'])
def grantListCreationPermissionHandler(message):
	user = GetUser(message.from_user.id)
	if user != False:
		userPermission = GetUserPermissionsValue(message.from_user.id)
		if IsUserSuperadmin(message.from_user.username) or UserPermission.IsAdmin(userPermission):
			args = message.text.split(' ')
			if len(args) == 2:
				newUserNickname = args[1]
				newUserId = getUserId(newUserNickname)
				if newUserId == False:
					#It looks like there's no user called this way
					bot.reply_to(message, "❌ Sembra che l'utente non sia registrato.\nÈ opportuno farlo registrare prima di promuoverlo e permettergli di creare liste!")
					return
				newUserpermission = GetUserPermissionsValue(newUserId)
				newUserpermission = UserPermission.SetListPermission(newUserpermission)
				res = SetUserPermissionsValue(newUserId, newUserpermission)
				if res == True:
					#Say OK
					bot.reply_to(message, "✅ Permesso di creazione liste assegnato!")
				else:
					#not ok
					bot.reply_to(message, "❌ Impossibile impostare il permesso!")
				return
			else:
				bot.reply_to(message, "❌ Utilizzo: /grantlist {@}username")
				return
	bot.reply_to(message, "❌ Error 403 - Unauthorized")

@bot.message_handler(commands=['revokelist'])
def revokeListCreationPermissionHandler(message):
	user = GetUser(message.from_user.id)
	if user != False:
		userPermission = GetUserPermissionsValue(message.from_user.id)
		if IsUserSuperadmin(message.from_user.username) or UserPermission.IsAdmin(userPermission) :
			args = message.text.split(' ')
			if len(args) == 2:
				oldUserNickname = args[1].replace('@','').lower()
				oldUserId = getUserId(oldUserNickname)
				if oldUserId == False:
					#It looks like there's no user called this way
					bot.reply_to(message, "❌ Sembra che l'utente non sia registrato.\nÈ opportuno farlo registrare prima di promuoverlo ad amministratore!")
					return
				oldUserpermission = GetUserPermissionsValue(oldUserId)
				oldUserpermission = UserPermission.RemoveListPermission(oldUserpermission)
				res = SetUserPermissionsValue(oldUserId, oldUserpermission)
				if res == True:
					#Say OK
					#If was creating list, abort
					oldstatus = GetUserStatusValue(oldUserId)
					if oldstatus == UserStatus.WAITING_FOR_LIST:
						setNewUserStatus(oldUserId,UserStatus.ACTIVE)
					bot.reply_to(message, "✅ Permesso revocato con successo!")
				else:
					#not ok
					bot.reply_to(message, "❌ Impossibile revocare il permesso!")
				return
			else:
				bot.reply_to(message, "❌ Utilizzo: /revokelist {@}username")
				return
	bot.reply_to(message, "❌ Error 403 - Unauthorized")


@bot.message_handler(commands=['ping'])
def pingHandler(message):
	if IsUserSuperadmin(message.from_user.username) or (GetUser(message.from_user.id) != False and UserPermission.IsAdmin(GetUserPermissionsValue(message.from_user.id))):
		
		markup = telebot.types.InlineKeyboardMarkup()
		markup.row(telebot.types.InlineKeyboardButton("❌ Chiudi", callback_data="deleteDis"))
		bot.reply_to(message, "🏓 Pong!", reply_markup=markup )

@bot.message_handler(commands=['die', 'crash'])
def dieHandler(message):
	if IsUserSuperadmin(message.from_user.username) or (GetUser(message.from_user.id) != False and UserPermission.IsAdmin(GetUserPermissionsValue(message.from_user.id))):
		bot.reply_to(message, "Autodestruction sequence initialized... \n💥 Poof! ✨")
		sys.exit(10)

@bot.message_handler(func=lambda m: True)
def genericMessageHandler(message):
	#get info about the user
	user = GetUser(message.from_user.id)
	if user != False:
		#The user is registred in DB
		UpdateNickname(message.from_user.id, message.from_user.username.lower())

		#Check for biography
		if user["Status"] == UserStatus.WAITING_FOR_BIOGRAPHY:
			#User is setting the Bio
			if message.chat.type == "private":
				dbC = dbConnection.cursor()
				res = dbC.execute('UPDATE Users SET Status=?, Biography=? WHERE ID = ?', (UserStatus.ACTIVE, message.text, message.from_user.id,) )
				msg = bot.reply_to(message, "✅ Biografia impostata con successo!")
				bot.delete_message(message.chat.id , message.reply_to_message.message_id)

				#Tries to force the user to reply to the message
			#TODO: Not sure about the order - needs to be checked
			elif (message.chat.type == "group" or message.chat.type == "supergroup") and message.reply_to_message != None and message.reply_to_message.from_user.id == botInfo.id:
				dbC = dbConnection.cursor()
				res = dbC.execute('UPDATE Users SET Status=?, Biography=? WHERE ID = ?', (UserStatus.ACTIVE, message.text, message.from_user.id,) )
				msg = bot.reply_to(message, "✅ Biografia impostata con successo!")
				bot.delete_message(message.chat.id , message.reply_to_message.message_id)

		#Check for list
		elif user["Status"] == UserStatus.WAITING_FOR_LIST:
			#User is creating a new list
			#TODO check for ASCII ONLY (RegEx?), replace spaces with underscores, 
			listName = message.text.lower()
			p = re.compile(r'[a-z0-9_\-]+', re.IGNORECASE)
			if message.chat.type == "private":
				if not p.match(listName):
					bot.reply_to(message, "Qualcosa è andato storto :c\n Il nome sembra contenre caratteri non permessi. Sono permesse solo lettere, numeri, underscores(_) e trattini")
					return
				success = CreateNewList(listName)
				if success:
					msg = bot.reply_to(message, "Lista creata con successo!")
				else:
					msg = bot.reply_to(message, "Qualcosa è andato storto :c\n Sei sicuro che non esista già una lista con lo stesso nome?")
				#Tries to force the user to reply to the message
				
			elif (message.chat.type == "group" or message.chat.type == "supergroup") and message.reply_to_message != None and message.reply_to_message.from_user.id == botInfo.id:
				if not p.match(listName):
					bot.reply_to(message, "Qualcosa è andato storto :c\n Il nome sembra contenre caratteri non permessi. Sono permesse solo lettere, numeri, underscores(_) e trattini")
					return
				success = CreateNewList(listName)
				if success:
					msg = bot.reply_to(message, "Lista creata con successo!")
				else:
					msg = bot.reply_to(message, "Qualcosa è andato storto :c\n Sei sicuro che non esista già una lista con lo stesso nome?")
		
		else:
			#Normal message, increment message counter
			#update lastseen
			UpdateLastSeen(message.from_user.id, time.strftime('%Y-%m-%d %H:%M:%S',
				#Telegram sends the date in a epoch format 
				#https://core.telegram.org/bots/api#message
				# Need to convert it
				#https://stackoverflow.com/a/12400584
				time.localtime(message.date)))

			if (message.chat.type == "group" or message.chat.type == "supergroup") and not message.from_user.is_bot and message.text != "":
				if message.text[0] == "#" or message.text[0] == "@" or message.text[0] == "." or message.text[0] == "!":
					listName = message.text.strip()[1:].lower().split(' ')[0]
					if ListExists(listName):
						users = GetListSubscribers(GetListID(listName))
						if users != False:
							variations = ["alla riscossa!", "all'attacco!", "che la conoscenza sia con voi!", "il mondo confida in voi!", 
							"che la vostra conoscenza possa illuminare la via!", "possa la vostra conoscenza aprire nuove vie!"]
							msg = "Gente di " + listName + ", " + random.choice(variations) + "\n"
							for user in users:
								msg = msg + "@"+GetUserNickname(user[0]) + ", "
							msg = msg[:len(msg)-2]
						else:
							msg = "La lista  " + listName + " non ha ancora nessun iscritto :c"
						bot.reply_to(message, msg)

				#Message counter
				if message.chat.id == Settings.ITGroup:
					#Increment IT group messages cunt
					IncrITGroupMessagesCount(message.from_user.id)
				elif message.chat.id == Settings.OTGroup:
					#Increment OT group messages cunt
						IncrOTGroupMessagesCount(message.from_user.id)
		dbConnection.commit()

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
	#Sample response
	# {'game_short_name': None, 'chat_instance': '5537587246343980605', 'id': '60524995438318427', 'from_user': {'id': 14092073, 'is_bot': False, 'first_name': 'Pandry', 'username': 'Pandry', 'last_name': None, 'language_code': 'en-US'}, 'message': {'content_type': 'text', 'message_id': 2910, 'from_user': <telebot.types.User object at 0x040BBB30>, 'date': 1541000520, 'chat': <telebot.types.Chat object at 0x040BBB10>, 'forward_from_chat': None, 'forward_from': None, 'forward_date': None, 'reply_to_message': <telebot.types.Message object at 0x040BBFB0>, 'edit_date': None, 'media_group_id': None, 'author_signature': None, 'text': 'Per impostare una biografia, scrivila in chat privata o rispondendomi', 'entities': None, 'caption_entities': None, 'audio': None, 'document': None, 'photo': None, 'sticker': None, 'video': None, 'video_note': None, 'voice': None, 'caption': None, 'contact': None, 'location': None, 'venue': None, 'new_chat_member': None, 'new_chat_members': None, 'left_chat_member': None, 'new_chat_title': None, 'new_chat_photo': None, 'delete_chat_photo': None, 'group_chat_created': None, 'supergroup_chat_created': None, 'channel_chat_created': None, 'migrate_to_chat_id': None, 'migrate_from_chat_id': None, 'pinned_message': None, 'invoice': None, 'successful_payment': None, 'connected_website': None, 'json': {'message_id': 2910, 'from': {'id': 676490981, 'is_bot': True, 'first_name': 'ScienzaBot', 'username': 'scienzati_bot'}, 'chat': {'id': -1001176680738, 'title': '@Scienza World Domination', 'type': 'supergroup'}, 'date': 1541000520, 'reply_to_message': {'message_id': 2909, 'from': {'id': 14092073,
	# 'is_bot': False, 'first_name': 'Pandry', 'username': 'Pandry', 'language_code': 'en-US'}, 'chat': {'id': -1001176680738, 'title': '@Scienza World Domination', 'type': 'supergroup'}, 'date': 1541000520, 'text': '/bio', 'entities': [{'offset': 0, 'length': 4, 'type': 'bot_command'}]}, 'text': 'Per impostare una biografia, scrivila in chat privata o rispondendomi'}}, 'data': 'annulla', 'inline_message_id': None}
	#
	#The call data can be edited, checks are needed
	user = GetUser(call.from_user.id)
	if user != False:
		#Check if is to abort bio
		if str.startswith(call.data == "aBio"):
			#Check if the guy who pressed is the same who asked to set the bio
			if call.message.reply_to_message != None and call.from_user.id == call.message.reply_to_message.from_user.id:
				#Check that the user needs to set the bio
				if user["Status"] == UserStatus.WAITING_FOR_BIOGRAPHY :
					success = abortNewBio(call.from_user.id)
					if success:
						markup = telebot.types.InlineKeyboardMarkup()
						bot.answer_callback_query(call.id, text="❌ Annullato", show_alert=True)
						bot.delete_message(call.message.chat.id , call.message.message_id)
						#bot.edit_message_text("Annullato." , call.message.chat.id , call.message.message_id, call.id, reply_markup=markup)
				else:
					bot.delete_message(call.message.chat.id , call.message.message_id)
		#Check if is to abort list creation
		elif str.startswith("aList"):
			#Check if the guy who pressed is the same who asked to set the bio
			if call.message.reply_to_message != None and call.from_user.id == call.message.reply_to_message.from_user.id:
				#Check that the user needs to set the bio
				if user["Status"] == UserStatus.WAITING_FOR_LIST :
					success = abortNewList(call.from_user.id)
					if success:
						markup = telebot.types.InlineKeyboardMarkup()
						bot.answer_callback_query(call.id, text="❌ Annullato", show_alert=True)
						bot.delete_message(call.message.chat.id , call.message.message_id)
						#bot.edit_message_text("Annullato." , call.message.chat.id , call.message.message_id, call.id, reply_markup=markup)
				else:
					bot.delete_message(call.message.chat.id , call.message.message_id)
		elif str.startswith("deleteDis"): 
			userPerm = GetUserPermissionsValue(call.from_user.id)
			if (IsUserSuperadmin(call.from_user.username) or UserPermission.IsAdmin(userPerm)) or call.message.reply_to_message != None and call.from_user.id == call.message.reply_to_message.from_user.id:
				bot.delete_message(call.message.chat.id , call.message.message_id)

		elif str.startswith( "ousub-"):
			if call.message.reply_to_message != None and call.from_user.id == call.message.reply_to_message.from_user.id:
				if user["Status"] == UserStatus.ACTIVE :
					#Show next n rows + offset, osub-{offset}
					#Safe data checks
					splittedString = call.data.split('-')
					if len(splittedString) == 2:
						if splittedString[1].isdigit():
							actualOffset=int(splittedString[1])
							if actualOffset%(Settings.subscriptionRows-1) == 0:
								lists = SubscribedLists(call.from_user.id, offset=int(actualOffset))
								markup = telebot.types.InlineKeyboardMarkup()
								if lists == False:
									bot.edit_message_text("Non sei iscritto a nessuna lista" , call.message.chat.id , call.message.message_id, call.id)
									return
								#Print the lists as inline buttons
								for ulist in lists:
									#																			sub-{id} => subscript to list {id}
									markup.row(telebot.types.InlineKeyboardButton(ulist["Name"], callback_data="usub-"+str(ulist["ID"])))
								#If there are still lists, print the page delimiter

								previousArrow = telebot.types.InlineKeyboardButton(f"⬅️", callback_data=f"ousub-"+str(int(actualOffset) - Settings.subscriptionRows+1))
								nextArrow = telebot.types.InlineKeyboardButton(f"➡️", callback_data=f"ousub-"+str(int(actualOffset) + Settings.subscriptionRows-1))
								emptyArrow = telebot.types.InlineKeyboardButton(" ", callback_data="ignore")
								deletePagination = telebot.types.InlineKeyboardButton("❌ Chiudi", callback_data="deleteDis")
								leftButton, rightButton = deletePagination,emptyArrow
								if int(actualOffset) >=Settings.subscriptionRows -1 or SubscribedLists(call.from_user.id, limit=1, offset=int(actualOffset + Settings.subscriptionRows-1)) != False:
									#Check if there are more list
									if SubscribedLists(call.from_user.id, limit=1, offset=int(actualOffset + Settings.subscriptionRows-1)) != False:
										rightButton = nextArrow
									if actualOffset - Settings.subscriptionRows +2 > 0:
										leftButton = previousArrow
								markup.row(leftButton, rightButton)
								bot.edit_message_text("Ecco un elenco delle liste attualmente alle quali sei iscritto al momento:\n(Per rimuovere la sottoscrizione, è sufficiente \"tapparla\" e confermare)" , call.message.chat.id , call.message.message_id, call.id, reply_markup=markup)
								return
					#Just go away
					bot.answer_callback_query(call.id, text="Just go away", show_alert=False, cache_time=999999)

		elif str.startswith( "orlist-"):
			if call.message.reply_to_message != None and call.from_user.id == call.message.reply_to_message.from_user.id:
				if user["Status"] == UserStatus.ACTIVE :
					#Show next n rows + offset, osub-{offset}
					#Safe data checks
					splittedString = call.data.split('-')
					if len(splittedString) == 2:
						if splittedString[1].isdigit():
							actualOffset=int(splittedString[1])
							if actualOffset%(Settings.subscriptionRows-1) == 0:


								liste = GetLists(offset=int(actualOffset))
								markup = telebot.types.InlineKeyboardMarkup()
								#Print the lists as inline buttons
								msg = "Random message padding"
								if liste == False:#TODO test
									msg = "Al momento non è presente nessuna lista.\nSi prega di riprovare in seguito."
								else:
									for ulist in liste:
										markup.row(telebot.types.InlineKeyboardButton(ulist["Name"], callback_data="rlist-"+str(ulist["ID"])))
									previousArrow = telebot.types.InlineKeyboardButton(f"⬅️", callback_data=f"orlist-"+str(int(actualOffset) - Settings.subscriptionRows+1))
									nextArrow = telebot.types.InlineKeyboardButton(f"➡️", callback_data=f"orlist-"+str(int(actualOffset) + Settings.subscriptionRows-1))
									emptyArrow = telebot.types.InlineKeyboardButton(" ", callback_data="ignore")
									deletePagination = telebot.types.InlineKeyboardButton("❌ Chiudi", callback_data="deleteDis")
									leftButton, rightButton = deletePagination,emptyArrow
									if int(actualOffset) >=Settings.subscriptionRows -1 or GetLists(limit=1, offset=int(actualOffset + Settings.subscriptionRows-1)) != False:
										#Check if there are more list
										if GetLists(limit=1, offset=int(actualOffset + Settings.subscriptionRows-1)) != False:
											rightButton = nextArrow
										if actualOffset - Settings.subscriptionRows +2 > 0:
											leftButton = previousArrow
									markup.row(leftButton, rightButton)
								#msg = bot.edit_message_reply_markup(call, msg, reply_markup=markup)
								bot.edit_message_text(msg , call.message.chat.id , call.message.message_id, call.id, reply_markup=markup)
								return
					#Just go away
					bot.answer_callback_query(call.id, text="Just go away", show_alert=False, cache_time=999999)

		elif str.startswith("crlist-"):
			if call.message.reply_to_message != None and call.from_user.id == call.message.reply_to_message.from_user.id:
				if user["Status"] == UserStatus.ACTIVE :
					splittedString = call.data.split('-')
					if len(splittedString) == 2:
						if splittedString[1].isdigit():
							listID=int(splittedString[1])
							#Remove subscription
							success = DeleteList(listID)
							if success:
								bot.answer_callback_query(call.id, text="✅ Eliminata", show_alert=False)
							else:
								bot.answer_callback_query(call.id, text="❌ Si è verificato un errore", show_alert=False)
							#Edit message back to list
							nc = call
							nc.data = "orlist-0"
							callback_query(nc)
							return 
			bot.answer_callback_query(call.id, text="Just go away", show_alert=False, cache_time=999999)


		elif str.startswith( "rlist-"):
			if call.message.reply_to_message != None and call.from_user.id == call.message.reply_to_message.from_user.id:
				if user["Status"] == UserStatus.ACTIVE :
					#Show next n rows + offset, osub-{offset}
					#Safe data checks
					splittedString = call.data.split('-')
					if len(splittedString) == 2:
						if splittedString[1].isdigit():
							listID=int(splittedString[1])
							msg="Sei sicuro di voler eliminare definitivamente la lista \"" + GetListName(listID) + "\"?"
							markup = telebot.types.InlineKeyboardMarkup()
							markup.row(
								telebot.types.InlineKeyboardButton(f"⬅️ No", callback_data=f"orlist-0"),
								telebot.types.InlineKeyboardButton(f"🗑 Elimina", callback_data=f"crlist-"+str(listID))
							)
							bot.edit_message_text(msg , call.message.chat.id , call.message.message_id, call.id, reply_markup=markup)
							return

		elif str.startswith( "cusub-"):
			if call.message.reply_to_message != None and call.from_user.id == call.message.reply_to_message.from_user.id:
				if user["Status"] == UserStatus.ACTIVE :
					splittedString = call.data.split('-')
					if len(splittedString) == 2:
						if splittedString[1].isdigit():
							listID=int(splittedString[1])
							#Remove subscription
							success = UnubscribeUserFromList(call.from_user.id, listID)
							if success:
								bot.answer_callback_query(call.id, text="✅ Disiscritto", show_alert=False)
							else:
								bot.answer_callback_query(call.id, text="❌ Si è verificato un errore", show_alert=False)
							#Edit message back to list
							nc = call
							nc.data = "ousub-0"
							callback_query(nc)
							return 
			bot.answer_callback_query(call.id, text="Just go away", show_alert=False, cache_time=999999)

		elif str.startswith( "usub-"):
			if call.message.reply_to_message != None and call.from_user.id == call.message.reply_to_message.from_user.id:
				if user["Status"] == UserStatus.ACTIVE :
					#Show next n rows + offset, osub-{offset}
					#Safe data checks
					splittedString = call.data.split('-')
					if len(splittedString) == 2:
						if splittedString[1].isdigit():
							listID=int(splittedString[1])
							msg="Sei sicuro di volerti disiscrivere dalla lista \"" + GetListName(listID) + "\"?"
							markup = telebot.types.InlineKeyboardMarkup()
							markup.row(
								telebot.types.InlineKeyboardButton(f"⬅️ No", callback_data=f"ousub-0"),
								telebot.types.InlineKeyboardButton(f"⚠️ Disiscriviti", callback_data=f"cusub-"+str(listID))
							)
							bot.edit_message_text(msg , call.message.chat.id , call.message.message_id, call.id, reply_markup=markup)
							return
			bot.answer_callback_query(call.id, text="Just go away", show_alert=False, cache_time=999999)
		elif str.startswith("osub-"):
			if call.message.reply_to_message != None and call.from_user.id == call.message.reply_to_message.from_user.id:
				if user["Status"] == UserStatus.ACTIVE :
					#Show next n rows + offset, osub-{offset}
					#Safe data checks
					splittedString = call.data.split('-')
					if len(splittedString) == 2:
						if splittedString[1].isdigit():
							actualOffset=int(splittedString[1])
							if actualOffset%(Settings.subscriptionRows-1) == 0:
								lists = AvailableListsToUser(call.from_user.id, offset=int(actualOffset))
								markup = telebot.types.InlineKeyboardMarkup()
								#Print the lists as inline buttons
								if lists == False:
									bot.edit_message_text("Al momento non è presente nessuna lista" , call.message.chat.id , call.message.message_id, call.id)
									return
								for ulist in lists:
									#																			sub-{id} => subscript to list {id}
									markup.row(telebot.types.InlineKeyboardButton(ulist["Name"], callback_data="sub-"+str(ulist["ID"])))
								#If there are still lists, print the page delimiter
								#if len(lists) > Settings.subscriptionRows-1:
								previousArrow = telebot.types.InlineKeyboardButton(f"⬅️", callback_data=f"osub-"+str(int(actualOffset) - Settings.subscriptionRows+1))
								nextArrow = telebot.types.InlineKeyboardButton(f"➡️", callback_data=f"osub-"+str(int(actualOffset) + Settings.subscriptionRows-1))
								emptyArrow = telebot.types.InlineKeyboardButton(" ", callback_data="ignore")
								deletePagination = telebot.types.InlineKeyboardButton("❌ Chiudi", callback_data="deleteDis")
								leftButton, rightButton = deletePagination,emptyArrow
								if int(actualOffset) >=Settings.subscriptionRows -1 or AvailableListsToUser(call.from_user.id, limit=1, offset=int( actualOffset + Settings.subscriptionRows-1)) != False:
									#Check if there are more list
									if AvailableListsToUser(call.from_user.id, limit=1, offset=int(actualOffset + Settings.subscriptionRows-1)) != False:
										rightButton = nextArrow
									if actualOffset - Settings.subscriptionRows +2 > 0:
										leftButton = previousArrow
								markup.row(leftButton, rightButton)
								#msg = bot.reply_to(message, msg, reply_markup=markup)
								bot.edit_message_reply_markup(call.message.chat.id , call.message.message_id, call.id, reply_markup=markup)
								return
					#Just go away
					bot.answer_callback_query(call.id, text="Just go away", show_alert=False, cache_time=999999)

		elif str.startswith( "sub-"):
			#Subscribe to list sub-{id}
			if call.message.reply_to_message != None and call.from_user.id == call.message.reply_to_message.from_user.id:
				if user["Status"] == UserStatus.ACTIVE :
					#Show next n rows + offset, osub-{offset}
					#Safe data checks
					splittedString = call.data.split('-')
					if len(splittedString) == 2:
						if splittedString[1].isdigit():
							listID=int(splittedString[1])
							success = SubscribeUserToList(call.from_user.id, listID)
							if success:
								bot.answer_callback_query(call.id, text="✅ Sottoscritto", show_alert=False)
							else:
								bot.answer_callback_query(call.id, text="❌ Si è verificato un errore", show_alert=False)
							#update message
							nc = call
							nc.data = "osub-0"
							callback_query(nc)
							return

@bot.inline_handler(func=lambda chosen_inline_result: True)
def getUserBioInlineQuery(inline_query):
	user = inline_query.query.lower()
	responses = []
	usersIDs = getUsersIdLike(user)
	for userid in usersIDs:
		userNick = GetUserNickname(userid[0])
		userBio = GetUserBio(userid[0])
		if userBio != None:
			responses.append(
				telebot.types.InlineQueryResultArticle(len(responses)+1,  userNick[0].upper() + userNick[1:] + "'s Bio: " + userBio,
														telebot.types.InputTextMessageContent(userNick[0].upper() + userNick[1:] + "'s Biography is \"" +userBio + "\""))
			)
		responses.append(
			telebot.types.InlineQueryResultArticle(len(responses)+1,  userNick[0].upper() + userNick[1:] + "'s permissions",
													telebot.types.InputTextMessageContent(getUserPermissionText(userid[0])))
		)
		
		
	bot.answer_inline_query(inline_query.id, responses)
    # Query message is text
###
#Starts the bot
###

bot.polling()
