from flask import Flask, render_template, request, jsonify
import pyodbc
import json
from datetime import datetime

app = Flask(__name__)

# Database configuration - Update these with your actual database credentials
DB_CONFIG = {
    'server': '192.168.101.25',
    'database': 'hkdb_data_bkp',
    'username': 'sa',
    'password': 'sa@123',
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
    
    # Add new method to verify login
    def verify_user_login(self, user_id):
        conn = self.get_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        try:
            cursor = conn.cursor()
            query = """
            SELECT id, name, email 
            FROM dbo.users 
            WHERE id = ?
            """
            cursor.execute(query, (user_id,))
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
                return {
                    "success": False,
                    "error": "User not found"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Query error: {str(e)}"
            }
        finally:
            conn.close()
    
    def get_user_details(self, user_id):
        conn = self.get_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        try:
            cursor = conn.cursor()
            query = """
            SELECT id, name, email, created_at
            FROM dbo.users 
            WHERE id = ?
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
    
    def get_order_status(self, user_id, order_id=None):
        conn = self.get_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        try:
            cursor = conn.cursor()
            if order_id:
                query = """
                SELECT order_id, order_status, order_date, total_amount, delivery_address
                FROM orders 
                WHERE user_id = ? AND order_id = ?
                """
                cursor.execute(query, (user_id, order_id))
            else:
                query = """
                SELECT order_id, order_status, order_date, total_amount, delivery_address
                FROM orders 
                WHERE user_id = ? 
                ORDER BY order_date DESC
                """
                cursor.execute(query, (user_id,))
            
            results = cursor.fetchall()
            orders = []
            
            for result in results:
                orders.append({
                    "order_id": result[0],
                    "status": result[1],
                    "order_date": result[2].strftime("%Y-%m-%d") if result[2] else None,
                    "total_amount": float(result[3]) if result[3] else 0,
                    "delivery_address": result[4]
                })
            
            return {"orders": orders}
        except Exception as e:
            return {"error": f"Query error: {str(e)}"}
        finally:
            conn.close()
    
    def get_cart_history(self, user_id):
        conn = self.get_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        try:
            cursor = conn.cursor()
            query = """
            SELECT c.cart_id, c.product_id, p.product_name, c.quantity, 
                   c.price, c.added_date, c.status
            FROM cart_history c
            LEFT JOIN products p ON c.product_id = p.product_id
            WHERE c.user_id = ?
            ORDER BY c.added_date DESC
            """
            cursor.execute(query, (user_id,))
            results = cursor.fetchall()
            
            cart_items = []
            for result in results:
                cart_items.append({
                    "cart_id": result[0],
                    "product_id": result[1],
                    "product_name": result[2],
                    "quantity": result[3],
                    "price": float(result[4]) if result[4] else 0,
                    "added_date": result[5].strftime("%Y-%m-%d") if result[5] else None,
                    "status": result[6]
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
        order_id = data.get('order_id')
        response = chatbot.get_order_status(user_id, order_id)
    elif action == 'cart_history':
        response = chatbot.get_cart_history(user_id)
    else:
        response = {"error": "Invalid action"}
    
    return jsonify(response)

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
        query = "SELECT order_id, order_status FROM orders WHERE user_id = ? ORDER BY order_date DESC"
        cursor.execute(query, (user_id,))
        results = cursor.fetchall()
        
        orders = [{"order_id": result[0], "status": result[1]} for result in results]
        return jsonify({"orders": orders})
    except Exception as e:
        return jsonify({"error": f"Query error: {str(e)}"})
    finally:
        conn.close()

@app.route('/verify_login', methods=['POST'])
def verify_login():
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({"success": False, "error": "User ID is required"})
    
    result = chatbot.verify_user_login(user_id)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
