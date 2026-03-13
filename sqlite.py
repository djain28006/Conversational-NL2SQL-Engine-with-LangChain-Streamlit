import sqlite3

# Connect to (or create) a database file named student.db
connection = sqlite3.connect("student.db")

# Create a cursor object to execute SQL commands
cursor = connection.cursor()

# Create table STUDENT
cursor.execute("""
CREATE TABLE IF NOT EXISTS STUDENT(
    NAME VARCHAR(25),
    CLASS VARCHAR(25),
    SECTION VARCHAR(25),
    MARKS INT
)
""")

# Insert records into the table
cursor.execute("INSERT INTO STUDENT VALUES('Danish','Data Science','A',90)")
cursor.execute("INSERT INTO STUDENT VALUES('Sanjay','Data Science','B',100)")
cursor.execute("INSERT INTO STUDENT VALUES('Harsh','Devops','A',80)")
cursor.execute("INSERT INTO STUDENT VALUES('Manish','Data Science','A',60)")
cursor.execute("INSERT INTO STUDENT VALUES('Jenish','Devops','B',75)")

# Display all records
print("The inserted records are:")
for row in cursor.execute("SELECT * FROM STUDENT"):
    print(row)

# Save changes and close the connection
connection.commit()
connection.close()