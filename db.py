import sqlite3

# create tables: users, recent searches, ratings
def db_create_tables():

    # Connect or create a new DB
    conn = sqlite3.connect('filmMatchingDB.db')

    # Create a new table for users
    conn.execute('''CREATE TABLE IF NOT EXISTS users
                    (id INTEGER PRIMARY KEY,
                    moderator BOOLEAN);
                    ''')

    # Create a new table for recent searches
    conn.execute('''CREATE TABLE IF NOT EXISTS recent_searches
                    (id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    category TEXT,
                    release_year INTEGER,
                    duration INTEGER,
                    cast TEXT,
                    search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id));''')

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

# add a new user to the database
def db_add_user(user_id, moderator=False):

    conn = sqlite3.connect('filmMatchingDB.db')
    cursor = conn.cursor()

    conn.execute("INSERT INTO users (id, moderator) VALUES (?, ?)", (user_id, moderator))
    conn.commit()
    conn.close()
    return user_id, cursor.rowcount > 0

# add a recent search for a user in the database
def db_add_recent_search(user_id, category, release_year, duration, cast):

    conn = sqlite3.connect('filmMatchingDB.db')
    cursor = conn.cursor()

    result = conn.execute("SELECT MAX(id) FROM recent_searches")
    max_id = result.fetchone()[0]

    if max_id is None:
        new_id = 1
    else:
        new_id = max_id + 1
    
    conn.execute("INSERT INTO recent_searches (id, user_id, category, release_year, duration, cast) VALUES (?, ?, ?, ?, ?, ?)",
                 (new_id, user_id, category, release_year, duration, cast))
    
    conn.commit()
    conn.close()
    return new_id


# Check if a user exists in the database
def db_user_exists(user_id):
    conn = sqlite3.connect('filmMatchingDB.db')
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users WHERE id = ?", (user_id,))
    user_count = cursor.fetchone()[0]

    conn.close()
    return user_count > 0

# add rating for a user and a movie in the database
def db_add_rating(user_id, movie_id, rating):

    if(not db_check_user_mod(user_id)):
        print(f"user {user_id} is NOT a moderator")
        return False

    conn = sqlite3.connect('filmMatchingDB.db')
    cursor = conn.cursor()

    result = conn.execute("SELECT MAX(id) FROM ratings")
    max_id = result.fetchone()[0]

    if max_id is None:
        new_id = 1

    else:
        new_id = max_id + 1
   
    conn.execute("INSERT INTO ratings (id, user_id, movie_id, rating) VALUES (?, ?, ?, ?)",
                 (new_id, user_id, movie_id, rating))
    
    conn.commit()
    conn.close()
    return new_id, cursor.rowcount > 0

# deletes a user
def db_delete_user(user_id):

    if(not db_check_user_mod(user_id)):
        print(f"user {user_id} is NOT a moderator")
        return False

    conn = sqlite3.connect('filmMatchingDB.db')
    cursor = conn.cursor()

    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

    return cursor.rowcount > 0

# deletes a search
def db_delete_search(user_id, search_id):

    if(not db_check_user_mod(user_id)):
        print(f"user {user_id} is NOT a moderator")
        return False

    conn = sqlite3.connect('filmMatchingDB.db')

    cursor = conn.cursor()
    cursor.execute('DELETE FROM recent_searches WHERE user_id = ? AND id = ?', (user_id, search_id))

    conn.commit()
    conn.close()

    return cursor.rowcount > 0

# deletes a rating
def delete_rating(user_id, rating_id):

    if(not db_check_user_mod(user_id)):
        print(f"user {user_id} is NOT a moderator")
        return False

    conn = sqlite3.connect('filmMatchingDB.db')

    cursor = conn.cursor()

    cursor.execute('DELETE FROM ratings WHERE user_id = ? AND id = ?', (user_id, rating_id))

    conn.commit()
    conn.close()

    return cursor.rowcount > 0

# checks if user is a moderator
def db_check_user_mod(user_id):

    conn = sqlite3.connect('filmMatchingDB.db')
    cursor = conn.cursor()

    cursor.execute('SELECT moderator FROM users WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result is not None and result[0] == 1:
        return True
    else:
        return False
    
# gets all users in db
def get_all_users():

    conn = sqlite3.connect('filmMatchingDB.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    return users

# gets all recent searches for all users in db
def get_all_recent_searches():

    conn = sqlite3.connect('filmMatchingDB.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM recent_searches')
    recent_searches = cursor.fetchall()
    return recent_searches

# get specific user's recent searches
def get_user_recent_searches(user_id):

    conn = sqlite3.connect('filmMatchingDB.db')
    cursor = conn.cursor()

    cursor.execute('SELECT id, category, release_year, duration, cast, search_date FROM recent_searches WHERE user_id = ?', (user_id,))
    user_recent_searches = cursor.fetchall()

    conn.close()
    return user_recent_searches

# get all ratings from db
def get_all_ratings():

    conn = sqlite3.connect('filmMatchingDB.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM ratings')
    ratings = cursor.fetchall()
    return ratings
