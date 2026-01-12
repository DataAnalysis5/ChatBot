from flask import Flask, render_template, request, jsonify
import pyodbc
from datetime import datetime

app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'server': '192.168.151.20',
    'database': 'hkdb_data_bkp',
    'username': '',
    'password': '',
    'driver': '{ODBC Driver 17 for SQL Server}'
}

class DatabaseChatbot:
    def __init__(self):
        self.connection_string = f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};UID={DB_CONFIG['username']};PWD={DB_CONFIG['password']}"
    
    def get_connection(self):
        try:
            return pyodbc.connect(self.connection_string)
        except Exception as e:
            print(f"Database connection error: {e}")
            return None

    # ✅ LOGIN USING MOBILE NUMBER FROM T_DATA_MST
    def verify_user_login(self, mobile_number):
        conn = self.get_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        try:
            cursor = conn.cursor()
            query = """
                SELECT DataID, DataName, DataEmail
                FROM dbo.T_DATA_MST
                WHERE DataLoginContactNo = ?
            """
            cursor.execute(query, (mobile_number,))
            result = cursor.fetchone()
            
            if result:
                return {
                    "success": True,
                    "user": {
                        "id": result[0],     
                        "name": result[1],    
                        "email": result[2]    
                    }
                }
            else:
                return {"success": False, "error": "User not found"}
        except Exception as e:
            return {"success": False, "error": f"Query error: {str(e)}"}
        finally:
            conn.close()

    # ✅ GET USER DETAILS FROM T_DATA_MST
    def get_user_details(self, user_id):
        conn = self.get_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        try:
            cursor = conn.cursor()
            query = """
                SELECT DataID, DataName, DataEmail, DataEntDt
                FROM dbo.T_DATA_MST
                WHERE DataID = ?
            """
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "email": result[2],
                    "created_at": result[3].strftime("%Y-%m-%d") if result[3] else None
                }
            else:
                return {"error": "User not found"}
        except Exception as e:
            return {"error": f"Query error: {str(e)}"}
        finally:
            conn.close()

    # ✅ ORDER STATUS CHECK
    def get_order_status_from_tracking(self, cart_mst_id):
        conn = self.get_connection()
        if not conn:
            return {"error": "Database connection failed"}

        try:
            cursor = conn.cursor()
            query_track = """
                SELECT TrackCartCommonID
                FROM T_CART_ITEM_TRACK WITH(NOLOCK)
                WHERE TrackCartMstId = ?
                ORDER BY TrackCartEntDt ASC
            """
            cursor.execute(query_track, (cart_mst_id,))
            rows = cursor.fetchall()

            if not rows:
                return {"statuses": []}

            last_common_id = rows[-1][0]

            query_status = """
                SELECT MstID, MstName
                FROM T_COMMON_MASTER WITH(NOLOCK)
                WHERE MstFlagID = 64 AND MstID = ?
            """
            cursor.execute(query_status, (last_common_id,))
            status_row = cursor.fetchone()

            if not status_row:
                return {"statuses": []}

            return {"statuses": [{"MstID": status_row[0], "MstName": status_row[1]}]}

        except Exception as e:
            return {"error": f"Query error: {str(e)}"}
        finally:
            conn.close()

    # ✅ CART HISTORY USING DataID
    def get_cart_history(self, user_id):
        conn = self.get_connection()
        if not conn:
            return {"error": "Database connection failed"}

        try:
            cursor = conn.cursor()
            query = """
                SELECT TOP 10 
                    itm.ItemID, itm.ItemDesc, itm.ItemSKU, itm.ItemMRP, itm.ItemEntDt, itm.ItemCngDt
                FROM T_CART_MST AS mst WITH(NOLOCK)
                JOIN T_CART_MST_ITEM AS mst_item WITH(NOLOCK) ON mst.CartID = mst_item.CartMstID
                JOIN T_ITEM_MST AS itm WITH(NOLOCK) ON mst_item.CartItemMstID = itm.ItemID
                WHERE mst.CartBillingDataID = ? AND mst.CartStatus = 'P'
                ORDER BY mst.CartChkOutDt DESC
            """
            cursor.execute(query, (user_id,))
            results = cursor.fetchall()

            cart_items = []
            for row in results:
                cart_items.append({
                    "item_id": row[0],
                    "product_name": row[1],
                    "item_sku": row[2],
                    "price": float(row[3]) if row[3] else 0,
                    "added_date": row[4].strftime("%Y-%m-%d") if row[4] else None,
                    "item_cng_dt": row[5].strftime("%Y-%m-%d") if row[5] else None,
                    "quantity": 1,
                    "status": "Purchased"
                })

            return {"cart_history": cart_items}

        except Exception as e:
            return {"error": f"Query error: {str(e)}"}
        finally:
            conn.close()


# Initialize chatbot
chatbot = DatabaseChatbot()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    action = data.get('action')
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required"})

    if action == 'user_details':
        response = chatbot.get_user_details(user_id)
    elif action == 'order_status':
        cart_mst_id = data.get('order_id')
        response = chatbot.get_order_status_from_tracking(cart_mst_id)
    elif action == 'cart_history':
        response = chatbot.get_cart_history(user_id)
    else:
        response = {"error": "Invalid action"}

    return jsonify(response)

# ✅ FETCH ORDERS USING DataID
@app.route('/get_user_orders', methods=['POST'])
def get_user_orders():
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required"})

    conn = chatbot.get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"})

    try:
        cursor = conn.cursor()
        query = """
            SELECT DISTINCT CartMstId
            FROM T_CART_MST_ITEM WITH(NOLOCK)
            JOIN T_CART_MST WITH(NOLOCK) ON T_CART_MST_ITEM.CartMstId = T_CART_MST.CartID
            WHERE T_CART_MST.CartBillingDataID = ?
            ORDER BY CartMstId DESC
        """
        cursor.execute(query, (user_id,))
        results = cursor.fetchall()

        orders = [{"order_id": result[0], "status": "Click to view"} for result in results]
        return jsonify({"orders": orders})

    except Exception as e:
        return jsonify({"error": f"Query error: {str(e)}"})
    finally:
        conn.close()

# ✅ LOGIN ROUTE UPDATED
@app.route('/verify_login', methods=['POST'])
def verify_login():
    data = request.json
    mobile_number = data.get('mobile_number')

    if not mobile_number:
        return jsonify({"success": False, "error": "Mobile number is required"})

    result = chatbot.verify_user_login(mobile_number)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
