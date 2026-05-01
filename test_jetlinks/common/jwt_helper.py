import jwt
import time

SECRET_KEY = "jetlinks-secret"

class JWTHelper:
    @staticmethod
    def decode(token, verify = True):
        """
        解码 Token
        :param verify: False 时不验证签名（用于查看内容）
        """
        try:
            if verify:
                return jwt.decode(token, SECRET_KEY, algorithms = ["HS256"])
            else:
                return 