from flask import Flask, request, render_template
import yfinance as yf
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time

app = Flask(__name__)

stocks = []
interval = 60
threshold = 2

@app.route('/')
def home():
    return render_template('index.html', stocks=stocks)

@app.route('/add_stock', methods=['POST'])
def add_stock():
    stock = request.form.get('stock')
    stocks.append(stock)
    return redirect('/')

@app.route('/set_parameters', methods=['POST'])
def set_parameters():
    global interval, threshold
    interval = int(request.form.get('interval'))
    threshold = int(request.form.get('threshold'))
    return redirect('/')

@app.route('/check_stock_price')
def check_stock_price():
    last_prices = {stock: 0 for stock in stocks}

    while True:
        for stock in stocks:
            try:
                # Fetch current price
                ticker = yf.Ticker(stock)
                current_price = ticker.history().tail(1)['Close'].iloc[0]

                # Check if the price has increased or decreased by the threshold in the last interval
                if abs(current_price - last_prices[stock]) >= threshold:
                    send_email(stock, current_price, current_price - last_prices[stock])

                # Update the last price
                last_prices[stock] = current_price

            except Exception as e:
                print(f"Error occurred while fetching the price for {stock}: {e}")

        # Wait for the specified interval
        time.sleep(interval)

def send_email(stock, price, change):
    try:
        msg = MIMEMultipart()
        msg['From'] = 'your_email@example.com'
        msg['To'] = 'your_email@example.com'
        msg['Subject'] = f'{stock} Stock Price Alert'
        direction = 'increased' if change > 0 else 'decreased'
        body = f'{stock} stock price has {direction} by ${threshold} in the last {interval} seconds. Current price is: ' + str(price)
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login('your_email@example.com', 'your_password')
        text = msg.as_string()
        server.sendmail('your_email@example.com', 'your_email@example.com', text)
        server.quit()

    except Exception as e:
        print(f"Error occurred while sending the email: {e}")

if __name__ == '__main__':
    app.run(debug=True)
