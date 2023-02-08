import mariadb
import config

#database = mariadb.connect(
#    host=config.sqlhost,
#    user=config.sqluser,
#    password=config.sqlpassword,
#    database=config.sqldatabase
#)

#cursor = database.cursor()

def execsql(query, args=()):
    database = mariadb.connect(
        host=config.sqlhost,
        user=config.sqluser,
        password=config.sqlpassword,
        database=config.sqldatabase
    )

    cursor = database.cursor()

    cursor.execute(query, args)
    database.commit()
    try:
        ret = cursor.fetchall()
    except:
        ret = []

    cursor.close()
    database.close()

    return ret

# sql = "select * from users;"

# cursor.execute(sql)

# result = cursor.fetchall()

# for x in result:
    # print(x)

# cursor.close()
# database.close()
