#!/usr/bin/env python3
"""
Complete Business Management System - Bug Fixed Version
"""

from flask import Flask, render_template, request, jsonify
import sqlite3
import json
from datetime import datetime, timedelta
import webbrowser
import threading

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('business_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        sold_quantity INTEGER DEFAULT 0,
        purchase_price REAL NOT NULL,
        selling_price REAL NOT NULL,
        supplier TEXT,
        date_added TEXT NOT NULL
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT NOT NULL,
        customer_name TEXT,
        customer_phone TEXT,
        items TEXT NOT NULL,
        total_amount REAL NOT NULL,
        payment_type TEXT NOT NULL,
        sale_date TEXT NOT NULL
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS credits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT,
        date TEXT NOT NULL
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT,
        date TEXT NOT NULL
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        reason TEXT,
        customer_name TEXT,
        return_date TEXT NOT NULL
    )''')
    
    conn.commit()
    conn.close()

@app.route('/')
def dashboard():
    conn = sqlite3.connect('business_system.db')
    cursor = conn.cursor()
    
    # Get dashboard data
    cursor.execute("SELECT SUM(total_amount) FROM sales")
    total_revenue = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM sales")
    total_sales = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(quantity) FROM stock")
    total_stock = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(amount) FROM expenses")
    total_expenses = cursor.fetchone()[0] or 0
    
    # Yearly growth data
    cursor.execute("""SELECT strftime('%Y', sale_date) as year, SUM(total_amount) 
                     FROM sales GROUP BY year ORDER BY year""")
    yearly_data = cursor.fetchall()
    
    # Monthly data for current year
    current_year = datetime.now().year
    cursor.execute("""SELECT strftime('%m', sale_date) as month, SUM(total_amount) 
                     FROM sales WHERE strftime('%Y', sale_date) = ? 
                     GROUP BY month ORDER BY month""", (str(current_year),))
    monthly_data = cursor.fetchall()
    
    # Top-selling products
    cursor.execute("SELECT product_name, sold_quantity FROM stock WHERE sold_quantity > 0 ORDER BY sold_quantity DESC LIMIT 5")
    top_products = cursor.fetchall()
    
    # Low stock alerts
    cursor.execute("SELECT product_name, quantity FROM stock WHERE quantity < 10")
    low_stock = cursor.fetchall()
    
    # Stock with sold quantities
    cursor.execute("SELECT * FROM stock ORDER BY id")
    stock_data = cursor.fetchall()
    
    conn.close()
    
    dashboard_data = {
        'total_revenue': total_revenue,
        'total_sales': total_sales,
        'total_stock': total_stock,
        'total_expenses': total_expenses,
        'profit': total_revenue - total_expenses,
        'yearly_data': yearly_data,
        'monthly_data': monthly_data,
        'stock_data': stock_data,
        'top_products': top_products,
        'low_stock': low_stock
    }
    
    return render_template('dashboard.html', data=dashboard_data)

@app.route('/stock')
def stock():
    conn = sqlite3.connect('business_system.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stock ORDER BY id")
    stocks = cursor.fetchall()
    conn.close()
    return render_template('stock_management.html', stocks=stocks)

@app.route('/add_stock', methods=['POST'])
def add_stock():
    try:
        data = request.json
        conn = sqlite3.connect('business_system.db')
        cursor = conn.cursor()
        
        cursor.execute('''INSERT INTO stock 
                         (product_name, quantity, purchase_price, selling_price, supplier, date_added)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (data['product_name'], data['quantity'], data['purchase_price'], 
                       data['selling_price'], data['supplier'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        if data.get('add_to_credit') and data['supplier']:
            total_cost = float(data['quantity']) * float(data['purchase_price'])
            cursor.execute('''INSERT INTO credits (type, name, amount, description, date)
                             VALUES (?, ?, ?, ?, ?)''',
                          ("supplier", data['supplier'], total_cost, f"Stock purchase: {data['product_name']}", 
                           datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_stock/<int:stock_id>', methods=['DELETE'])
def delete_stock(stock_id):
    try:
        conn = sqlite3.connect('business_system.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT product_name FROM stock WHERE id = ?", (stock_id,))
        stock = cursor.fetchone()
        
        if not stock:
            conn.close()
            return jsonify({'success': False, 'error': 'Stock item not found'})
        
        cursor.execute("DELETE FROM stock WHERE id = ?", (stock_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Deleted {stock[0]} successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/edit_stock/<int:stock_id>', methods=['PUT'])
def edit_stock(stock_id):
    try:
        data = request.json
        conn = sqlite3.connect('business_system.db')
        cursor = conn.cursor()
        
        cursor.execute('''UPDATE stock SET 
                         product_name = ?, quantity = ?, purchase_price = ?, 
                         selling_price = ?, supplier = ?
                         WHERE id = ?''',
                      (data['product_name'], data['quantity'], data['purchase_price'], 
                       data['selling_price'], data['supplier'], stock_id))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Stock updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_stock/<int:stock_id>')
def get_stock(stock_id):
    try:
        conn = sqlite3.connect('business_system.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stock WHERE id = ?", (stock_id,))
        stock = cursor.fetchone()
        conn.close()
        
        if stock:
            return jsonify({
                'success': True,
                'stock': {
                    'id': stock[0],
                    'product_name': stock[1],
                    'quantity': stock[2],
                    'sold_quantity': stock[3],
                    'purchase_price': stock[4],
                    'selling_price': stock[5],
                    'supplier': stock[6]
                }
            })
        return jsonify({'success': False, 'error': 'Stock not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/sales')
def sales():
    conn = sqlite3.connect('business_system.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales ORDER BY id DESC")
    sales_data = cursor.fetchall()
    conn.close()
    return render_template('smart_sales.html', sales=sales_data)

@app.route('/get_product_info/<product_name>')
def get_product_info(product_name):
    try:
        conn = sqlite3.connect('business_system.db')
        cursor = conn.cursor()
        cursor.execute("SELECT selling_price, quantity FROM stock WHERE LOWER(product_name) = LOWER(?)", (product_name,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({'success': True, 'price': result[0], 'available_qty': result[1]})
        else:
            return jsonify({'success': False, 'message': 'Product not found in stock'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_all_stock')
def get_all_stock():
    try:
        conn = sqlite3.connect('business_system.db')
        cursor = conn.cursor()
        cursor.execute("SELECT product_name, quantity, selling_price FROM stock WHERE quantity > 0 ORDER BY product_name")
        stock_items = cursor.fetchall()
        conn.close()
        
        stock_data = []
        for item in stock_items:
            stock_data.append({
                'product_name': item[0],
                'quantity': item[1],
                'selling_price': item[2]
            })
        
        return jsonify({'success': True, 'stock': stock_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/create_sale', methods=['POST'])
def create_sale():
    try:
        data = request.json
        conn = sqlite3.connect('business_system.db')
        cursor = conn.cursor()
        
        invoice_no = f"QS{datetime.now().strftime('%Y%m%d%H%M%S')}"
        total_amount = sum(item['total'] for item in data['items'])
        
        cursor.execute('''INSERT INTO sales 
                         (invoice_no, customer_name, customer_phone, items, total_amount, payment_type, sale_date)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (invoice_no, data.get('customer', 'Walk-in Customer'), '', json.dumps(data['items']), 
                       total_amount, 'cash', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        for item in data['items']:
            # Handle both 'name' and 'product_name' keys for compatibility
            product_name = item.get('name') or item.get('product_name')
            cursor.execute("SELECT quantity FROM stock WHERE LOWER(product_name) = LOWER(?)", (product_name,))
            stock = cursor.fetchone()
            if stock and stock[0] >= item['quantity']:
                cursor.execute("UPDATE stock SET quantity = quantity - ?, sold_quantity = sold_quantity + ? WHERE LOWER(product_name) = LOWER(?)", 
                              (item['quantity'], item['quantity'], product_name))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'invoice': invoice_no})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/returns')
def returns():
    conn = sqlite3.connect('business_system.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM returns ORDER BY return_date DESC")
    returns_data = cursor.fetchall()
    conn.close()
    return render_template('returns.html', returns=returns_data)

@app.route('/add_return', methods=['POST'])
def add_return():
    try:
        data = request.json
        conn = sqlite3.connect('business_system.db')
        cursor = conn.cursor()
        
        # Add to returns table
        cursor.execute('''INSERT INTO returns 
                         (product_name, quantity, reason, customer_name, return_date)
                         VALUES (?, ?, ?, ?, ?)''',
                      (data['product_name'], data['quantity'], data['reason'], 
                       data['customer_name'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        # Add back to stock
        cursor.execute("SELECT id FROM stock WHERE LOWER(product_name) = LOWER(?)", (data['product_name'],))
        stock_exists = cursor.fetchone()
        
        if stock_exists:
            cursor.execute("UPDATE stock SET quantity = quantity + ? WHERE LOWER(product_name) = LOWER(?)", 
                          (data['quantity'], data['product_name']))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Return processed and stock updated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def send_whatsapp_invoice(phone, invoice_no, customer_name, items, total_amount):
    try:
        # Create beautiful invoice message
        message = "🧾 *INVOICE RECEIPT* 🧾\n"
        message += "═══════════════════════════\n\n"
        
        message += f"📋 *Invoice:* {invoice_no}\n"
        message += f"👤 *Customer:* {customer_name or 'Valued Customer'}\n"
        message += f"📅 *Date:* {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        
        message += "📦 *ITEMS PURCHASED:*\n"
        message += "─────────────────────────────\n"
        
        for i, item in enumerate(items, 1):
            message += f"{i}. *{item['product_name']}*\n"
            message += f"   Qty: {item['quantity']} × PKR {item['price']} = *PKR {item['total']}*\n\n"
        
        message += "─────────────────────────────\n"
        message += f"💰 *TOTAL: PKR {total_amount}*\n"
        message += "─────────────────────────────\n\n"
        
        message += "🙏 *Thank you for your business!*\n"
        message += "📞 Contact us for support\n"
        message += "✨ We appreciate you! ✨"
        
        # Clean phone and create WhatsApp URL
        clean_phone = phone.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Encode message for URL
        import urllib.parse
        encoded_message = urllib.parse.quote(message)
        
        url = f"https://wa.me/{clean_phone}?text={encoded_message}"
        
        # Open WhatsApp
        webbrowser.open(url)
        print(f"WhatsApp invoice sent to {phone}")
        
    except Exception as e:
        print(f"WhatsApp error: {e}")

@app.route('/create_invoice', methods=['POST'])
def create_invoice():
    try:
        data = request.json
        conn = sqlite3.connect('business_system.db')
        cursor = conn.cursor()
        
        # Validate stock before creating invoice
        errors = []
        for item in data['items']:
            cursor.execute("SELECT quantity FROM stock WHERE LOWER(product_name) = LOWER(?)", (item['product_name'],))
            result = cursor.fetchone()
            
            if not result:
                errors.append(f"Product '{item['product_name']}' not found in stock")
            elif result[0] < item['quantity']:
                errors.append(f"Insufficient stock for '{item['product_name']}'. Available: {result[0]}")
        
        if errors:
            conn.close()
            return jsonify({'success': False, 'errors': errors})
        
        # Create invoice if validation passes
        invoice_no = f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}"
        total_amount = sum(item['total'] for item in data['items'])
        
        cursor.execute('''INSERT INTO sales 
                         (invoice_no, customer_name, customer_phone, items, total_amount, payment_type, sale_date)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (invoice_no, data['customer_name'], data.get('customer_phone'), json.dumps(data['items']), 
                       total_amount, data['payment_type'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        for item in data['items']:
            cursor.execute("UPDATE stock SET quantity = quantity - ?, sold_quantity = sold_quantity + ? WHERE LOWER(product_name) = LOWER(?)", 
                          (item['quantity'], item['quantity'], item['product_name']))
        
        if data['payment_type'] == 'credit':
            cursor.execute('''INSERT INTO credits (type, name, amount, description, date)
                             VALUES (?, ?, ?, ?, ?)''',
                          ("customer", data['customer_name'], total_amount, f"Sale: {invoice_no}", 
                           datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
        conn.close()
        
        if data.get('customer_phone') and data.get('send_whatsapp'):
            threading.Thread(target=send_whatsapp_invoice, 
                            args=(data['customer_phone'], invoice_no, data['customer_name'], 
                                 data['items'], total_amount), daemon=True).start()
        
        return jsonify({'success': True, 'invoice_no': invoice_no})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/simple_create_sale', methods=['POST'])
def simple_create_sale():
    try:
        data = request.json
        conn = sqlite3.connect('business_system.db')
        cursor = conn.cursor()
        
        # Validate stock
        errors = []
        for item in data['items']:
            cursor.execute("SELECT quantity FROM stock WHERE LOWER(product_name) = LOWER(?)", (item['product_name'],))
            result = cursor.fetchone()
            
            if not result:
                errors.append(f"Product '{item['product_name']}' not found")
            elif result[0] < item['quantity']:
                errors.append(f"Only {result[0]} {item['product_name']} available")
        
        if errors:
            conn.close()
            return jsonify({'success': False, 'errors': errors})
        
        # Create sale
        invoice_no = f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}"
        total_amount = sum(item['total'] for item in data['items'])
        
        cursor.execute('''INSERT INTO sales 
                         (invoice_no, customer_name, customer_phone, items, total_amount, payment_type, sale_date)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (invoice_no, data.get('customer_name', 'Walk-in'), data.get('customer_phone'), 
                       json.dumps(data['items']), total_amount, data['payment_type'], 
                       datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        # Update stock
        for item in data['items']:
            cursor.execute("UPDATE stock SET quantity = quantity - ?, sold_quantity = sold_quantity + ? WHERE LOWER(product_name) = LOWER(?)", 
                          (item['quantity'], item['quantity'], item['product_name']))
        
        # Add credit if needed
        if data['payment_type'] == 'credit' and data.get('customer_name'):
            cursor.execute('''INSERT INTO credits (type, name, amount, description, date)
                             VALUES (?, ?, ?, ?, ?)''',
                          ("customer", data['customer_name'], total_amount, f"Invoice: {invoice_no}", 
                           datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
        conn.close()
        
        # Send WhatsApp if requested
        if data.get('send_whatsapp') and data.get('customer_phone'):
            threading.Thread(target=send_whatsapp_invoice, 
                            args=(data['customer_phone'], invoice_no, data.get('customer_name', 'Valued Customer'), 
                                 data['items'], total_amount), daemon=True).start()
        
        return jsonify({'success': True, 'invoice_no': invoice_no, 'total': total_amount})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_sales_summary')
def get_sales_summary():
    try:
        conn = sqlite3.connect('business_system.db')
        cursor = conn.cursor()
        
        # Today's sales
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_amount), 0) FROM sales WHERE DATE(sale_date) = ?", (today,))
        today_sales = cursor.fetchone()
        
        # Total sales
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_amount), 0) FROM sales")
        total_sales = cursor.fetchone()
        
        # Recent sales
        cursor.execute("SELECT invoice_no, customer_name, total_amount, sale_date FROM sales ORDER BY sale_date DESC LIMIT 5")
        recent_sales = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'today_count': today_sales[0],
            'today_amount': today_sales[1],
            'total_count': total_sales[0],
            'total_amount': total_sales[1],
            'recent_sales': recent_sales
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/analytics')
def analytics():
    conn = sqlite3.connect('business_system.db')
    cursor = conn.cursor()
    
    # Basic metrics
    cursor.execute("SELECT SUM(total_amount) FROM sales")
    total_revenue = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM sales")
    total_sales = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(quantity * purchase_price) FROM stock")
    stock_value = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(amount) FROM expenses")
    total_expenses = cursor.fetchone()[0] or 0
    
    # Monthly data for current year
    current_year = datetime.now().year
    cursor.execute("""SELECT strftime('%m', sale_date) as month, 
                            SUM(total_amount) as revenue,
                            (SELECT SUM(amount) FROM expenses WHERE strftime('%Y-%m', date) = strftime('%Y-%m', sales.sale_date)) as expenses
                     FROM sales 
                     WHERE strftime('%Y', sale_date) = ? 
                     GROUP BY month ORDER BY month""", (str(current_year),))
    monthly_data = cursor.fetchall()
    
    # Yearly profit/loss data
    cursor.execute("""SELECT strftime('%Y', sale_date) as year, 
                            SUM(total_amount) as revenue,
                            (SELECT SUM(amount) FROM expenses WHERE strftime('%Y', date) = strftime('%Y', sales.sale_date)) as expenses
                     FROM sales 
                     GROUP BY year ORDER BY year""")
    yearly_data = cursor.fetchall()
    
    # Process data for charts
    monthly_profit_loss = []
    for month_data in monthly_data:
        month, revenue, expenses = month_data
        expenses = expenses or 0
        profit = revenue - expenses
        monthly_profit_loss.append((month, revenue, expenses, profit))
    
    yearly_profit_loss = []
    for year_data in yearly_data:
        year, revenue, expenses = year_data
        expenses = expenses or 0
        profit = revenue - expenses
        yearly_profit_loss.append((year, revenue, expenses, profit))
    
    conn.close()
    
    analytics_data = {
        'total_revenue': total_revenue,
        'total_sales': total_sales,
        'stock_value': stock_value,
        'total_expenses': total_expenses,
        'profit_loss': total_revenue - total_expenses - stock_value,
        'monthly_data': monthly_profit_loss,
        'yearly_data': yearly_profit_loss,
        'current_year': current_year
    }
    
    return render_template('profit_loss_analytics.html', data=analytics_data)

@app.route('/ledger')
def ledger():
    conn = sqlite3.connect('business_system.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM credits ORDER BY date DESC")
    credits_data = cursor.fetchall()
    conn.close()
    return render_template('ledger_management.html', credits=credits_data)

@app.route('/expenses')
def expenses():
    conn = sqlite3.connect('business_system.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses ORDER BY date DESC")
    expenses_data = cursor.fetchall()
    conn.close()
    return render_template('expense_management.html', expenses=expenses_data)

@app.route('/add_expense', methods=['POST'])
def add_expense():
    try:
        data = request.json
        conn = sqlite3.connect('business_system.db')
        cursor = conn.cursor()
        
        cursor.execute('''INSERT INTO expenses (category, amount, description, date)
                         VALUES (?, ?, ?, ?)''',
                      (data['category'], data['amount'], data['description'], 
                       datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/ai_chat', methods=['POST'])
def ai_chat():
    try:
        query = request.json['query'].lower()
        
        conn = sqlite3.connect('business_system.db')
        cursor = conn.cursor()
        
        if "stock" in query or "inventory" in query:
            if "low" in query:
                cursor.execute("SELECT product_name, quantity FROM stock WHERE quantity < 10")
                low_stock = cursor.fetchall()
                response = "Low stock: " + ", ".join([f"{item[0]} ({item[1]} left)" for item in low_stock]) if low_stock else "All items well stocked!"
            else:
                cursor.execute("SELECT COUNT(*), SUM(quantity) FROM stock")
                result = cursor.fetchone()
                response = f"Total: {result[0]} products, {result[1]} items in stock"
        elif "sales" in query or "revenue" in query:
            if "today" in query:
                cursor.execute("SELECT COUNT(*), SUM(total_amount) FROM sales WHERE DATE(sale_date) = DATE('now')")
                result = cursor.fetchone()
                response = f"Today: {result[0]} sales, PKR {result[1] or 0} revenue"
            else:
                cursor.execute("SELECT COUNT(*), SUM(total_amount) FROM sales")
                result = cursor.fetchone()
                response = f"Total: {result[0]} sales, PKR {result[1] or 0} revenue"
        elif "profit" in query:
            cursor.execute("SELECT SUM(total_amount) FROM sales")
            revenue = cursor.fetchone()[0] or 0
            cursor.execute("SELECT SUM(amount) FROM expenses")
            expenses = cursor.fetchone()[0] or 0
            cursor.execute("SELECT SUM(quantity * purchase_price) FROM stock")
            stock_cost = cursor.fetchone()[0] or 0
            profit = revenue - expenses - stock_cost
            response = f"Profit: PKR {profit} (Revenue: PKR {revenue}, Expenses: PKR {expenses}, Stock: PKR {stock_cost})"
        else:
            response = "I can help with stock, sales, profit analysis. Ask me anything!"
        
        conn.close()
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/print_invoice/<invoice_no>')
def print_invoice(invoice_no):
    try:
        conn = sqlite3.connect('business_system.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sales WHERE invoice_no = ?", (invoice_no,))
        sale = cursor.fetchone()
        conn.close()
        
        if sale:
            items = json.loads(sale[4])
            return render_template('elegant_invoice.html', sale=sale, items=items)
        return "Invoice not found", 404
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    init_db()
    print("Business Management System Starting...")
    print("Dashboard: http://localhost:5000")
    print("Sales: http://localhost:5000/sales")
    print("Stock: http://localhost:5000/stock")
    print("\nSystem ready! Create sales with WhatsApp integration.")
    app.run(debug=True, host='0.0.0.0', port=5000)