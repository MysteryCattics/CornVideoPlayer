import sys
import os
import argparse
import ffmpeg
import tempfile
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

HEADER = b"CORNFORMATv1----"

version = "v1.0.0"

def make_key(password: str, salt: bytes) -> bytes:
    if not password:
        password = "default_empty_password"
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

def create_crn(mp4_path: str, output_path: str, password: str = "") -> str:
    """
    Шифрует MP4 файл и сохраняет его по точной указанной траектории output_path.
    """
    if not os.path.isfile(mp4_path):
        raise FileNotFoundError(f"Файл не найден: {mp4_path}")
        
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(mp4_path, "rb") as f:
        data = f.read()

    salt = os.urandom(16)
    iv = os.urandom(16)
    key = make_key(password, salt)

    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(data) + encryptor.finalize()

    with open(output_path, "wb") as f:
        f.write(HEADER)
        f.write(salt)
        f.write(iv)
        f.write(encrypted)

    return output_path

def decrypt_crn(crn_path: str, output_path: str, password: str = "") -> str:
    """
    Расшифровывает файл .crn обратно в .mp4 по точной указанной траектории output_path.
    """
    if not os.path.isfile(crn_path):
        raise FileNotFoundError(f"Файл не найден: {crn_path}")

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(crn_path, "rb") as f:
        header = f.read(len(HEADER))
        if header != HEADER:
            raise ValueError("Неверный формат файла или заголовок поврежден")

        salt = f.read(16)
        iv = f.read(16)
        encrypted_data = f.read()

    key = make_key(password, salt)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

    with open(output_path, "wb") as f:
        f.write(decrypted_data)

    return output_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Corn Video Processor (CVP)", 
        add_help=False
    )

    parser.add_argument("-p", "--password", type=str, default="", help="Password")
    parser.add_argument("-i", "--input", type=str, required=False, help="Input file path")
    parser.add_argument("-o", "--output", type=str, required=False, help="Output file path")
    parser.add_argument("-n", "--no-convert", action="store_true", help="Skip FFmpeg conversion")
    parser.add_argument("-h", "--help", action="store_true", help="Output help")
    parser.add_argument("-v", "--version", action="store_true", help="Show the current version")

    help_formula = """
Usage:
cvp -i <input_file> -p <password> -o <output_file>  

-p, --password: Password for encryption/decryption (optional).
-i, --input: Input file path.
-o, --output: Output file path.
-n, --no-convert: Don't convert through FFmpeg.
-h, --help: Show this message.
-v, --version: Show the current version

Example:
cvp -i input.mp4 -p pass123 -o custom_name.crn

\033[33m Warning: \033[0m If you don't specify a password, the default password will be used.
\033[33m Warning: \033[0m FFmpeg is REQUIRED for video conversion.
"""

    args = parser.parse_args()

    if args.help or not args.input or not args.output:
        print(help_formula)
        sys.exit(0)

    if args.version:
        print(version)
        sys.exit(0)

    input_file = args.input
    output_file = args.output
    password = args.password
    no_convert = args.no_convert

    # РЕЖИМ 1: Зашифровка (MP4 -> CRN)
    if input_file.lower().endswith(".mp4") and output_file.lower().endswith(".crn"):
        target_mp4 = input_file
        temp_mp4_path = None

        try:
            if not no_convert:
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
                    temp_mp4_path = tmp_file.name

                print("Processing video with FFmpeg...")
                (
                    ffmpeg
                    .input(input_file)
                    .output(temp_mp4_path, vcodec='libx264', acodec='aac')
                    .overwrite_output()
                    .run(quiet=True)
                )
                target_mp4 = temp_mp4_path

            create_crn(target_mp4, output_file, password)
            print(f"\033[32mSuccess:\033[0m File encrypted to {output_file}")

        except ffmpeg.Error as e:
            print(f"\033[31mFFmpeg Error:\033[0m {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\033[31mError:\033[0m {e}")
            sys.exit(1)
        finally:
            if temp_mp4_path and os.path.exists(temp_mp4_path):
                os.remove(temp_mp4_path)

    # РЕЖИМ 2: Расшифровка (CRN -> MP4)
    elif input_file.lower().endswith(".crn") and output_file.lower().endswith(".mp4"):
        try:
            decrypt_crn(input_file, output_file, password)
            print(f"\033[32mSuccess:\033[0m File decrypted to {output_file}")
        except PermissionError as e:
            print(f"\033[31mAccess Denied:\033[0m {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\033[31mDecryption Error:\033[0m {e}")
            sys.exit(1)

    else:
        print("\033[31mError:\033[0m Unsupported format combination. Use .mp4 -> .crn or .crn -> .mp4")

