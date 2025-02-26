#!/bin/bash

# Create the main project directory
mkdir -p stock_trading_system

# Navigate into the project directory
cd stock_trading_system || exit

# Create Python files and requirements.txt
touch app.py models.py database.py price_generator.py requirements.txt

# Create the templates directory and HTML files
mkdir -p templates
cd templates || exit
touch base.html index.html login.html register.html portfolio.html admin_dashboard.html create_stock.html
cd ..

# Create the static directory and CSS file
mkdir -p static
cd static || exit
touch styles.css

echo "Project structure created successfully!"
