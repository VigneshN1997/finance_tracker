#!/usr/bin/env python3
"""
Initialize a blank database for the Finance Tracker application.
This script will:
1. Create a NEW database with a unique name (preserves existing databases)
2. Create all tables with the correct schema
3. Optionally create a default admin user
4. Tell you the database name to use in config.py

Run this script when setting up the application for the first time.
"""

import os
from datetime import datetime
from app import app, db
from models import User

def init_db(db_name=None, create_admin=False):
    """Initialize a fresh database with all tables."""
    
    # Generate a unique database name if not provided
    if not db_name:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        db_name = f'finance_tracker_{timestamp}.db'
    
    # Ensure .db extension
    if not db_name.endswith('.db'):
        db_name += '.db'
    
    print("="*60)
    print("Finance Tracker - Database Initialization")
    print("="*60)
    print(f"\n📊 Creating new database: {db_name}")
    
    # Check if database already exists
    if os.path.exists(db_name):
        print(f"⚠️  WARNING: Database '{db_name}' already exists!")
        response = input("Overwrite it? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("\n❌ Database initialization cancelled.")
            return None
        os.remove(db_name)
        print("✓ Old database removed")
    
    # Temporarily override the database URI
    original_uri = app.config['SQLALCHEMY_DATABASE_URI']
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_name}'
    
    with app.app_context():
        # Reinitialize db with new URI
        db.init_app(app)
        
        # Create all tables
        print("\n📊 Creating database tables...")
        db.create_all()
        print("✓ All tables created successfully")
        
        # List all tables created
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"\n✓ Created {len(tables)} tables:")
        for table in tables:
            print(f"  • {table}")
        
        # Optionally create admin user
        if create_admin:
            print("\n👤 Creating admin user...")
            admin = User(email='admin@example.com', display_currency='USD')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✓ Admin user created")
            print("  Email: admin@example.com")
            print("  Password: admin123")
            print("  ⚠️  IMPORTANT: Change this password after first login!")
    
    # Restore original URI
    app.config['SQLALCHEMY_DATABASE_URI'] = original_uri
    
    print("\n" + "="*60)
    print("✓ Database initialization complete!")
    print("="*60)
    print(f"\n📁 Database created: {db_name}")
    print(f"📍 Full path: {os.path.abspath(db_name)}")
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print(f"\n1. Update config.py to use this database:")
    print(f"   SQLALCHEMY_DATABASE_URI = 'sqlite:///{db_name}'")
    print("\n2. Run the application:")
    print("   python3 app.py")
    print("\n3. Create a new user account via the signup page")
    print("   OR run create_demo_data.py for demo data")
    print()
    
    return db_name

if __name__ == '__main__':
    import sys
    
    print("="*60)
    print("Finance Tracker - Database Initialization")
    print("="*60)
    
    # Parse command line arguments for admin flag
    create_admin = '--admin' in sys.argv or '-a' in sys.argv
    
    # Prompt for database name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    default_name = f'finance_tracker_{timestamp}.db'
    
    print(f"\nEnter database name (press Enter for default):")
    print(f"Default: {default_name}")
    db_name = input("Database name: ").strip()
    
    # Use default if empty
    if not db_name:
        db_name = default_name
        print(f"Using default: {db_name}")
    
    # Ensure .db extension
    if not db_name.endswith('.db'):
        db_name += '.db'
        print(f"Added .db extension: {db_name}")
    
    # Ask about admin user if not specified in command line
    if not create_admin:
        admin_response = input("\nCreate admin user? (yes/no): ").strip().lower()
        create_admin = admin_response in ['yes', 'y']
    
    print("\n" + "-"*60)
    print("Summary:")
    print(f"  Database name: {db_name}")
    print(f"  Create admin: {'Yes' if create_admin else 'No'}")
    print("-"*60)
    
    response = input("\nContinue? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        result = init_db(db_name=db_name, create_admin=create_admin)
        if result:
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        print("\n❌ Database initialization cancelled.")
        sys.exit(0)
