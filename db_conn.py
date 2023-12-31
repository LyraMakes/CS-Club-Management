import mysql.connector
from typing import List


class connect:
    def __init__(self, host, user, passwd, db):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.db = db
        self.mydb = mysql.connector.connect(
            host=self.host,
            user=self.user,
            passwd=self.passwd,
            database=self.db
        )
        self.mycursor = self.mydb.cursor()

    def validate_address(self, address: List[str]):
        self.mycursor.execute(f"SELECT * FROM addresses")
        myresult = self.mycursor.fetchall()
        for x in myresult:
            if all([a == b for a, b in zip(address, x[1:])]):
                return x[0]
        # Address not found. Add it to the database
        return self.create_address(address)

    def create_address(self, address: List[str]) -> int:
        sql = "INSERT INTO addresses (Line1, Line2, Line3, Line4) VALUES (%s, %s, %s, %s)"
        val = tuple(address)
        self.mycursor.execute(sql, val)
        self.mydb.commit()
        return self.mycursor.lastrowid

    def create_record(self, id: int, creator: str,
                      approver: str, type: str, 
                      return_addr: List[str], 
                      tax: float | int, fees: float | int, 
                      status: str, total: float | int, date: str) -> int:
        sql = """
        insert into record (id, createdDate, creator, approver, recordType, return_addr, tax, fees, total, statusID)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        addr_id = self.validate_address(return_addr)
        status_id = self.get_status_id(status)
        val = (id, date, creator, approver, type, addr_id, tax, fees, total, status_id)
        self.mycursor.execute(sql, val)
        self.mydb.commit()
        return self.mycursor.lastrowid

    def create_item(self, record_id: int, item: str, quantity: int, price: float | int) -> int:
        # Get the current list of items
        self.mycursor.execute(f"SELECT * FROM items WHERE record_id = {record_id}")
        myresult = self.mycursor.fetchall()
        # Get the next id
        if len(myresult) == 0:
            id = 1
        else:
            id = max([x[0] for x in myresult]) + 1
        sql = "INSERT INTO items (recordID, line, desc, ammt, qty, total) VALUES (%s, %s, %s, %s, %s, %s)"
        val = (record_id, id, item, price, quantity, price * quantity)
        self.mycursor.execute(sql, val)
        self.mydb.commit()
        return self.mycursor.lastrowid
    
    def update_record(self, **data) -> int:
        sql = "UPDATE record SET "
        params = []
        for key, value in data.items():
            if key == "return_addr":
                value = self.validate_address(value)
            if key == "status":
                key='statusID'
                value = self.get_status_id(value)
            if key == "creator":
                continue
            params.append(f"{key} = '{value}'")
        sql += ", ".join(params)

    def get_status_id(self, status: str) -> int:
        self.mycursor.execute(f"SELECT * FROM statuses WHERE statusDesc = '{status}'")
        myresult = self.mycursor.fetchall()
        if len(myresult) == 0:
            return self.create_status(status)
        return myresult[0][0]
    
    def get_status(self, status_id: int) -> str:
        self.mycursor.execute(f"SELECT * FROM statuses WHERE statusID = {status_id}")
        myresult = self.mycursor.fetchall()
        return myresult[0][1]
    
    def get_next_invoice_id(self) -> int:
        sql = "SELECT * FROM record WHERE recordType = 'invoice'"
        self.mycursor.execute(sql)
        myresult = self.mycursor.fetchall()
        if len(myresult) == 0:
            return 1
        return max([x[0] for x in myresult]) + 1        

    def get_records(self) -> List:
        record_sql = """
        SELECT a.id, a.createdDate, a.creator, a.approver, a.recordType, a.tax, a.fees, 
        a.total, a.return_addr, b.statusDesc FROM record a, statuses b 
        WHERE a.statusID = b.statusID
        """
        line_sql = """
        SELECT line, `desc`, ammt, qty, total FROM inv_line WHERE recordID = %s
        """
        self.mycursor.execute(record_sql)
        myresult = self.mycursor.fetchall()
        records = []
        for record in myresult:
            self.mycursor.execute(line_sql, (record[0],))
            lines = self.mycursor.fetchall()
            records.append({
                "id": str(record[0]),
                "date": format_date(record[1]),
                "creator": record[2],
                "approver": record[3],
                "type": record[4],
                "tax": record[5],
                "fees": record[6],
                "total": record[7],
                "status": record[9],
                "li": [],
                "return_addr": self.get_address(record[8])
                }
            )
            for x in lines:
                print(x)
                records[-1]["li"].append({
                    "line": x[0],
                    "desc": x[1],
                    "ammt": x[2],
                    "qty": x[3],
                    "total": x[4]
                })
        return records
    
    def get_record_by_id(self, id: int) -> dict:
        record_sql = """
        SELECT a.id, a.createdDate, a.creator, a.approver, a.recordType, a.tax, a.fees, 
        a.total, a.return_addr, b.statusDesc FROM record a, statuses b 
        WHERE a.statusID = b.statusID and a.id = %s
        """
        line_sql = """
        SELECT line, `desc`, ammt, qty, total FROM inv_line WHERE recordID = %s
        """
        values = (id,)
        self.mycursor.execute(record_sql, values)
        records = self.mycursor.fetchone()
        self.mycursor.execute(line_sql, values)
        lines = self.mycursor.fetchall()
        record = {
            "id": str(records[0]),
            "date": format_date(records[1]),
            "creator": records[2],
            "approver": records[3],
            "type": records[4],
            "tax": records[5],
            "fees": records[6],
            "total": records[7],
            "status": records[9],
            "li": [],
            "return_addr": self.get_address(records[8])
        }
        for x in lines:
            record["li"].append({
                "line": x[0],
                "desc": x[1],
                "ammt": x[2],
                "qty": x[3],
                "total": x[4]
            })
    
    def get_address(self, id: int) -> List[str]:
        if id is None:
            return ["", "", "", ""]
        self.mycursor.execute(f"SELECT * FROM addresses WHERE addrSeq = {id}")
        myresult = self.mycursor.fetchall()
        return myresult[0][1:]
    
    def update_line(self, recordID, lineNum, **data) -> int:
        sql = "SELECT * FROM inv_line WHERE recordID = %s"
        values = (recordID,)
        self.mycursor.execute(sql, values)
        myresult = self.mycursor.fetchall()
        if len(myresult) == 0:
            return self.create_item(recordID, **data)
        sql = "UPDATE inv_line SET "
        params = []
        for key, value in data.items():
            if key == "line":
                continue
            params.append(f"`{key}` = '{value}'")
        sql += ", ".join(params)
        sql += f" WHERE recordID = {recordID} AND line = {lineNum}"
        print(sql)
        self.mycursor.execute(sql)
        self.mydb.commit()


def format_date(date: str) -> str:
    return date.strftime("%d %b, %Y")