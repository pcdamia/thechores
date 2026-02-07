import bcrypt

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def hash_security_answer(answer):
    """Hash a security answer"""
    return hash_password(answer)

def verify_security_answer(answer, answer_hash):
    """Verify a security answer"""
    return verify_password(answer, answer_hash)
