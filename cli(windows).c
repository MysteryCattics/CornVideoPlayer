```c
#define _CRT_SECURE_NO_WARNINGS

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <windows.h>
#include <bcrypt.h>
#include <shlwapi.h>

#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "shlwapi.lib")

#define HEADER "CORNFORMATv1----"
#define HEADER_LEN 16

#define SALT_LEN 16
#define IV_LEN 16
#define KEY_LEN 32

#define PBKDF2_ITERATIONS 200000

#define MAX_PATH_BUFFER 32768

static const char* VERSION = "v1.0.0";

/*
    ============================================================
    Utility functions
    ============================================================
*/

static void print_error(const char* message)
{
    fprintf(stderr, "\033[31mError:\033[0m %s\n", message);
}

static void print_win_error(const char* message, NTSTATUS status)
{
    fprintf(
        stderr,
        "\033[31mError:\033[0m %s (0x%08lX)\n",
        message,
        (unsigned long)status
    );
}

static int file_exists(const char* path)
{
    DWORD attributes = GetFileAttributesA(path);

    return attributes != INVALID_FILE_ATTRIBUTES &&
           !(attributes & FILE_ATTRIBUTE_DIRECTORY);
}

static int get_file_size(FILE* file, uint64_t* size)
{
    LARGE_INTEGER li;

    if (!file || !size)
        return 0;

    if (_fseeki64(file, 0, SEEK_END) != 0)
        return 0;

    li.QuadPart = _ftelli64(file);

    if (li.QuadPart < 0)
        return 0;

    *size = (uint64_t)li.QuadPart;

    if (_fseeki64(file, 0, SEEK_SET) != 0)
        return 0;

    return 1;
}

/*
    ============================================================
    Directory creation
    ============================================================
*/

static int create_directory_recursive(const char* path)
{
    char buffer[MAX_PATH_BUFFER];
    size_t length;
    char* p;

    if (!path || !path[0])
        return 1;

    length = strlen(path);

    if (length >= sizeof(buffer))
    {
        print_error("Path is too long.");
        return 0;
    }

    strcpy(buffer, path);

    /*
        Remove trailing slash.
    */
    while (length > 0 &&
           (buffer[length - 1] == '\\' || buffer[length - 1] == '/'))
    {
        buffer[length - 1] = '\0';
        length--;
    }

    /*
        Handle drive letter:
        C:\folder
        ^
    */
    p = buffer;

    if (length >= 2 && buffer[1] == ':')
        p = buffer + 2;

    for (; *p; p++)
    {
        if (*p == '\\' || *p == '/')
        {
            char old = *p;

            *p = '\0';

            if (strlen(buffer) > 0)
            {
                DWORD attributes = GetFileAttributesA(buffer);

                if (attributes == INVALID_FILE_ATTRIBUTES)
                {
                    if (!CreateDirectoryA(buffer, NULL))
                    {
                        DWORD error = GetLastError();

                        if (error != ERROR_ALREADY_EXISTS)
                        {
                            fprintf(
                                stderr,
                                "\033[31mError:\033[0m Cannot create directory: %s\n",
                                buffer
                            );
                            return 0;
                        }
                    }
                }
                else if (!(attributes & FILE_ATTRIBUTE_DIRECTORY))
                {
                    fprintf(
                        stderr,
                        "\033[31mError:\033[0m Path component is not a directory: %s\n",
                        buffer
                    );
                    return 0;
                }
            }

            *p = old;
        }
    }

    {
        DWORD attributes = GetFileAttributesA(buffer);

        if (attributes == INVALID_FILE_ATTRIBUTES)
        {
            if (!CreateDirectoryA(buffer, NULL))
            {
                DWORD error = GetLastError();

                if (error != ERROR_ALREADY_EXISTS)
                    return 0;
            }
        }
        else if (!(attributes & FILE_ATTRIBUTE_DIRECTORY))
        {
            return 0;
        }
    }

    return 1;
}

static int create_output_directory(const char* output_path)
{
    char directory[MAX_PATH_BUFFER];
    char* last_slash1;
    char* last_slash2;
    char* last_slash;

    if (!output_path || !output_path[0])
        return 0;

    if (strlen(output_path) >= sizeof(directory))
    {
        print_error("Output path is too long.");
        return 0;
    }

    strcpy(directory, output_path);

    last_slash1 = strrchr(directory, '\\');
    last_slash2 = strrchr(directory, '/');

    if (last_slash1 && last_slash2)
        last_slash = last_slash1 > last_slash2 ? last_slash1 : last_slash2;
    else if (last_slash1)
        last_slash = last_slash1;
    else
        last_slash = last_slash2;

    if (!last_slash)
        return 1;

    /*
        "C:\file.mp4" -> "C:\"
    */
    if (last_slash == directory + 2 &&
        directory[1] == ':')
    {
        last_slash[1] = '\0';
    }
    else
    {
        *last_slash = '\0';
    }

    if (directory[0] == '\0')
        return 1;

    return create_directory_recursive(directory);
}

/*
    ============================================================
    Random bytes
    ============================================================
*/

static int random_bytes(unsigned char* buffer, DWORD length)
{
    BCRYPT_ALG_HANDLE algorithm = NULL;
    NTSTATUS status;

    status = BCryptOpenAlgorithmProvider(
        &algorithm,
        BCRYPT_RNG_ALGORITHM,
        NULL,
        0
    );

    if (status != 0)
    {
        print_win_error(
            "Could not open Windows random number provider.",
            status
        );
        return 0;
    }

    status = BCryptGenRandom(
        algorithm,
        buffer,
        length,
        0
    );

    BCryptCloseAlgorithmProvider(algorithm, 0);

    if (status != 0)
    {
        print_win_error(
            "Could not generate random bytes.",
            status
        );
        return 0;
    }

    return 1;
}

/*
    ============================================================
    PBKDF2-HMAC-SHA256
    Compatible with Python cryptography PBKDF2HMAC
    ============================================================
*/

static int derive_key_pbkdf2(
    const char* password,
    const unsigned char* salt,
    unsigned char* output_key
)
{
    const char* actual_password;

    BCRYPT_ALG_HANDLE algorithm = NULL;
    NTSTATUS status;

    if (!password || password[0] == '\0')
        actual_password = "default_empty_password";
    else
        actual_password = password;

    status = BCryptOpenAlgorithmProvider(
        &algorithm,
        BCRYPT_SHA256_ALGORITHM,
        NULL,
        BCRYPT_ALG_HANDLE_HMAC_FLAG
    );

    if (status != 0)
    {
        print_win_error(
            "Could not open SHA-256 provider.",
            status
        );
        return 0;
    }

    status = BCryptDeriveKeyPBKDF2(
        algorithm,

        (PUCHAR)actual_password,
        (ULONG)strlen(actual_password),

        (PUCHAR)salt,
        SALT_LEN,

        PBKDF2_ITERATIONS,

        output_key,
        KEY_LEN,

        0
    );

    BCryptCloseAlgorithmProvider(algorithm, 0);

    if (status != 0)
    {
        print_win_error(
            "PBKDF2 key derivation failed.",
            status
        );
        return 0;
    }

    return 1;
}

/*
    ============================================================
    AES-256-CFB
    Compatible with Python:

        Cipher(
            algorithms.AES(key),
            modes.CFB(iv)
        )

    CFB uses a 16-byte IV for AES.
    ============================================================
*/

static int aes_cfb_process(
    const unsigned char* key,
    const unsigned char* iv,
    unsigned char* data,
    size_t data_length,
    int encrypt
)
{
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_KEY_HANDLE key_handle = NULL;

    PUCHAR key_object = NULL;

    DWORD key_object_length = 0;
    DWORD result_length = 0;

    NTSTATUS status;

    unsigned char iv_copy[IV_LEN];

    if (data_length > ULONG_MAX)
    {
        print_error("File is too large for this Windows CNG operation.");
        return 0;
    }

    /*
        Open AES provider.
    */
    status = BCryptOpenAlgorithmProvider(
        &algorithm,
        BCRYPT_AES_ALGORITHM,
        NULL,
        0
    );

    if (status != 0)
    {
        print_win_error(
            "Could not open AES provider.",
            status
        );
        return 0;
    }

    /*
        Set AES CFB mode.
    */
    status = BCryptSetProperty(
        algorithm,
        BCRYPT_CHAINING_MODE,
        (PUCHAR)BCRYPT_CHAIN_MODE_CFB,
        (ULONG)sizeof(BCRYPT_CHAIN_MODE_CFB),
        0
    );

    if (status != 0)
    {
        print_win_error(
            "Could not set AES CFB mode.",
            status
        );

        BCryptCloseAlgorithmProvider(algorithm, 0);
        return 0;
    }

    /*
        Get required key object size.
    */
    status = BCryptGetProperty(
        algorithm,
        BCRYPT_OBJECT_LENGTH,
        (PUCHAR)&key_object_length,
        sizeof(key_object_length),
        &result_length,
        0
    );

    if (status != 0)
    {
        print_win_error(
            "Could not get AES key object size.",
            status
        );

        BCryptCloseAlgorithmProvider(algorithm, 0);
        return 0;
    }

    key_object = (PUCHAR)HeapAlloc(
        GetProcessHeap(),
        0,
        key_object_length
    );

    if (!key_object)
    {
        print_error("Could not allocate AES key memory.");

        BCryptCloseAlgorithmProvider(algorithm, 0);
        return 0;
    }

    /*
        Create AES-256 key.
    */
    status = BCryptGenerateSymmetricKey(
        algorithm,
        &key_handle,
        key_object,
        key_object_length,
        (PUCHAR)key,
        KEY_LEN,
        0
    );

    if (status != 0)
    {
        print_win_error(
            "Could not create AES key.",
            status
        );

        HeapFree(GetProcessHeap(), 0, key_object);
        BCryptCloseAlgorithmProvider(algorithm, 0);

        return 0;
    }

    /*
        BCryptEncrypt/Decrypt modifies the IV.

        Python's Cipher object receives the IV without modifying
        the original byte array, so we use a copy.
    */
    memcpy(iv_copy, iv, IV_LEN);

    if (encrypt)
    {
        status = BCryptEncrypt(
            key_handle,
            data,
            (ULONG)data_length,
            NULL,
            iv_copy,
            IV_LEN,
            data,
            (ULONG)data_length,
            &result_length,
            0
        );
    }
    else
    {
        status = BCryptDecrypt(
            key_handle,
            data,
            (ULONG)data_length,
            NULL,
            iv_copy,
            IV_LEN,
            data,
            (ULONG)data_length,
            &result_length,
            0
        );
    }

    if (status != 0)
    {
        print_win_error(
            encrypt
                ? "AES encryption failed."
                : "AES decryption failed.",
            status
        );

        BCryptDestroyKey(key_handle);
        HeapFree(GetProcessHeap(), 0, key_object);
        BCryptCloseAlgorithmProvider(algorithm, 0);

        return 0;
    }

    /*
        For CFB, ciphertext/plaintext length must remain identical.
    */
    if (result_length != (DWORD)data_length)
    {
        print_error("AES operation returned an unexpected data size.");

        BCryptDestroyKey(key_handle);
        HeapFree(GetProcessHeap(), 0, key_object);
        BCryptCloseAlgorithmProvider(algorithm, 0);

        return 0;
    }

    BCryptDestroyKey(key_handle);

    HeapFree(
        GetProcessHeap(),
        0,
        key_object
    );

    BCryptCloseAlgorithmProvider(
        algorithm,
        0
    );

    return 1;
}

/*
    ============================================================
    MP4 -> CRN
    ============================================================
*/

static int create_crn(
    const char* mp4_path,
    const char* output_path,
    const char* password
)
{
    FILE* input = NULL;
    FILE* output = NULL;

    uint64_t file_size64;

    size_t file_size;

    unsigned char* data = NULL;

    unsigned char salt[SALT_LEN];
    unsigned char iv[IV_LEN];
    unsigned char key[KEY_LEN];

    size_t bytes_read;

    if (!file_exists(mp4_path))
    {
        fprintf(
            stderr,
            "\033[31mError:\033[0m File not found: %s\n",
            mp4_path
        );
        return 0;
    }

    if (!create_output_directory(output_path))
    {
        print_error("Could not create output directory.");
        return 0;
    }

    input = fopen(mp4_path, "rb");

    if (!input)
    {
        fprintf(
            stderr,
            "\033[31mError:\033[0m Could not open input file: %s\n",
            mp4_path
        );
        return 0;
    }

    if (!get_file_size(input, &file_size64))
    {
        fclose(input);

        print_error("Could not determine input file size.");
        return 0;
    }

    /*
        malloc uses size_t.
    */
    if (file_size64 > SIZE_MAX)
    {
        fclose(input);

        print_error("Input file is too large.");
        return 0;
    }

    file_size = (size_t)file_size64;

    /*
        Python can encrypt an empty file, so allow size == 0.
    */
    if (file_size > 0)
    {
        data = (unsigned char*)malloc(file_size);

        if (!data)
        {
            fclose(input);

            print_error("Could not allocate memory for input file.");
            return 0;
        }

        bytes_read = fread(
            data,
            1,
            file_size,
            input
        );

        if (bytes_read != file_size)
        {
            free(data);
            fclose(input);

            print_error("Could not read complete input file.");
            return 0;
        }
    }

    fclose(input);

    /*
        Generate salt and IV exactly as Python does:
            os.urandom(16)
            os.urandom(16)
    */
    if (!random_bytes(salt, SALT_LEN) ||
        !random_bytes(iv, IV_LEN))
    {
        free(data);
        return 0;
    }

    /*
        PBKDF2-HMAC-SHA256.
    */
    if (!derive_key_pbkdf2(password, salt, key))
    {
        free(data);
        return 0;
    }

    /*
        AES-256-CFB.
    */
    if (file_size > 0)
    {
        if (!aes_cfb_process(
                key,
                iv,
                data,
                file_size,
                1))
        {
            free(data);
            return 0;
        }
    }

    output = fopen(output_path, "wb");

    if (!output)
    {
        free(data);

        fprintf(
            stderr,
            "\033[31mAccess Denied:\033[0m Could not open output file: %s\n",
            output_path
        );

        return 0;
    }

    /*
        CRN format:

        HEADER
        SALT
        IV
        ENCRYPTED DATA
    */

    if (fwrite(
            HEADER,
            1,
            HEADER_LEN,
            output) != HEADER_LEN)
    {
        fclose(output);
        free(data);

        print_error("Could not write CRN header.");
        return 0;
    }

    if (fwrite(
            salt,
            1,
            SALT_LEN,
            output) != SALT_LEN)
    {
        fclose(output);
        free(data);

        print_error("Could not write CRN salt.");
        return 0;
    }

    if (fwrite(
            iv,
            1,
            IV_LEN,
            output) != IV_LEN)
    {
        fclose(output);
        free(data);

        print_error("Could not write CRN IV.");
        return 0;
    }

    if (file_size > 0)
    {
        if (fwrite(
                data,
                1,
                file_size,
                output) != file_size)
        {
            fclose(output);
            free(data);

            print_error("Could not write encrypted data.");
            return 0;
        }
    }

    if (fclose(output) != 0)
    {
        free(data);

        print_error("Could not close output file.");
        return 0;
    }

    free(data);

    return 1;
}

/*
    ============================================================
    CRN -> MP4
    ============================================================
*/

static int decrypt_crn(
    const char* crn_path,
    const char* output_path,
    const char* password
)
{
    FILE* input = NULL;
    FILE* output = NULL;

    uint64_t file_size64;
    uint64_t encrypted_size64;

    size_t encrypted_size;

    unsigned char header[HEADER_LEN];

    unsigned char salt[SALT_LEN];
    unsigned char iv[IV_LEN];
    unsigned char key[KEY_LEN];

    unsigned char* encrypted_data = NULL;

    size_t bytes_read;

    if (!file_exists(crn_path))
    {
        fprintf(
            stderr,
            "\033[31mError:\033[0m File not found: %s\n",
            crn_path
        );
        return 0;
    }

    if (!create_output_directory(output_path))
    {
        print_error("Could not create output directory.");
        return 0;
    }

    input = fopen(crn_path, "rb");

    if (!input)
    {
        fprintf(
            stderr,
            "\033[31mError:\033[0m Could not open CRN file: %s\n",
            crn_path
        );
        return 0;
    }

    if (!get_file_size(input, &file_size64))
    {
        fclose(input);

        print_error("Could not determine CRN file size.");
        return 0;
    }

    /*
        Minimum valid CRN:

        16 header
        16 salt
        16 IV

        = 48 bytes
    */
    if (file_size64 < HEADER_LEN + SALT_LEN + IV_LEN)
    {
        fclose(input);

        print_error("CRN file is too small or corrupted.");
        return 0;
    }

    /*
        Read header.
    */
    if (fread(
            header,
            1,
            HEADER_LEN,
            input) != HEADER_LEN)
    {
        fclose(input);

        print_error("Could not read CRN header.");
        return 0;
    }

    if (memcmp(
            header,
            HEADER,
            HEADER_LEN) != 0)
    {
        fclose(input);

        print_error(
            "Invalid file format or header corrupted."
        );
        return 0;
    }

    /*
        Read salt.
    */
    if (fread(
            salt,
            1,
            SALT_LEN,
            input) != SALT_LEN)
    {
        fclose(input);

        print_error("Could not read CRN salt.");
        return 0;
    }

    /*
        Read IV.
    */
    if (fread(
            iv,
            1,
            IV_LEN,
            input) != IV_LEN)
    {
        fclose(input);

        print_error("Could not read CRN IV.");
        return 0;
    }

    encrypted_size64 =
        file_size64 -
        HEADER_LEN -
        SALT_LEN -
        IV_LEN;

    if (encrypted_size64 > SIZE_MAX)
    {
        fclose(input);

        print_error("Encrypted file is too large.");
        return 0;
    }

    encrypted_size = (size_t)encrypted_size64;

    if (encrypted_size > 0)
    {
        encrypted_data =
            (unsigned char*)malloc(encrypted_size);

        if (!encrypted_data)
        {
            fclose(input);

            print_error(
                "Could not allocate memory for encrypted data."
            );
            return 0;
        }

        bytes_read = fread(
            encrypted_data,
            1,
            encrypted_size,
            input
        );

        if (bytes_read != encrypted_size)
        {
            free(encrypted_data);
            fclose(input);

            print_error(
                "Could not read complete encrypted data."
            );
            return 0;
        }
    }

    fclose(input);

    /*
        Derive exactly the same key as Python.
    */
    if (!derive_key_pbkdf2(password, salt, key))
    {
        free(encrypted_data);
        return 0;
    }

    /*
        AES-256-CFB decryption.
    */
    if (encrypted_size > 0)
    {
        if (!aes_cfb_process(
                key,
                iv,
                encrypted_data,
                encrypted_size,
                0))
        {
            free(encrypted_data);
            return 0;
        }
    }

    output = fopen(output_path, "wb");

    if (!output)
    {
        free(encrypted_data);

        fprintf(
            stderr,
            "\033[31mAccess Denied:\033[0m Could not open output file: %s\n",
            output_path
        );

        return 0;
    }

    if (encrypted_size > 0)
    {
        if (fwrite(
                encrypted_data,
                1,
                encrypted_size,
                output) != encrypted_size)
        {
            fclose(output);
            free(encrypted_data);

            print_error("Could not write decrypted file.");
            return 0;
        }
    }

    if (fclose(output) != 0)
    {
        free(encrypted_data);

        print_error("Could not close output file.");
        return 0;
    }

    free(encrypted_data);

    return 1;
}

/*
    ============================================================
    Extension helpers
    ============================================================
*/

static int ends_with_ignore_case(
    const char* string,
    const char* suffix
)
{
    size_t string_length;
    size_t suffix_length;

    if (!string || !suffix)
        return 0;

    string_length = strlen(string);
    suffix_length = strlen(suffix);

    if (string_length < suffix_length)
        return 0;

    return _stricmp(
        string + string_length - suffix_length,
        suffix
    ) == 0;
}

/*
    ============================================================
    FFmpeg
    ============================================================
*/

static int create_temp_mp4(
    const char* input,
    char* output,
    size_t output_size
)
{
    char temp_dir[MAX_PATH_BUFFER];
    char temp_base[MAX_PATH];

    DWORD result;

    if (!GetTempPathA(
            (DWORD)sizeof(temp_dir),
            temp_dir))
    {
        print_error("Could not get Windows temporary directory.");
        return 0;
    }

    result = GetTempFileNameA(
        temp_dir,
        "cvp",
        0,
        temp_base
    );

    if (result == 0)
    {
        print_error("Could not create temporary filename.");
        return 0;
    }

    /*
        GetTempFileName creates the file immediately.

        Remove that file because FFmpeg will create the .mp4.
    */
    DeleteFileA(temp_base);

    if (strlen(temp_base) + 4 >= output_size)
    {
        print_error("Temporary path is too long.");
        return 0;
    }

    snprintf(
        output,
        output_size,
        "%s.mp4",
        temp_base
    );

    /*
        Escape is handled by quoting the paths.
    */
    {
        char command[MAX_PATH_BUFFER * 2];

        int written = snprintf(
            command,
            sizeof(command),
            "ffmpeg -i \"%s\" -vcodec libx264 -acodec aac -y \"%s\" >nul 2>&1",
            input,
            output
        );

        if (written < 0 ||
            (size_t)written >= sizeof(command))
        {
            print_error("FFmpeg command is too long.");
            return 0;
        }

        printf("Processing video with FFmpeg...\n");

        result = (DWORD)system(command);

        if (result != 0)
        {
            fprintf(
                stderr,
                "\033[31mFFmpeg Error:\033[0m FFmpeg execution failed\n"
            );

            DeleteFileA(output);

            return 0;
        }
    }

    return 1;
}

/*
    ============================================================
    Help
    ============================================================
*/

static void print_help(void)
{
    printf(
        "\n"
        "Usage:\n"
        "cvp -i <input_file> -p <password> -o <output_file>\n"
        "\n"
        "-p, --password: Password for encryption/decryption (optional).\n"
        "-i, --input: Input file path.\n"
        "-o, --output: Output file path.\n"
        "-n, --no-convert: Don't convert through FFmpeg.\n"
        "-h, --help: Show this message.\n"
        "-v, --version: Show the current version.\n"
        "\n"
        "Example:\n"
        "cvp -i input.mp4 -p pass123 -o custom_name.crn\n"
        "\n"
        "\033[33mWarning:\033[0m "
        "If you don't specify a password, the default password will be used.\n"
        "\033[33mWarning:\033[0m "
        "FFmpeg is REQUIRED for video conversion.\n"
        "\n"
    );
}

/*
    ============================================================
    Main
    ============================================================
*/

int main(int argc, char* argv[])
{
    const char* password = "";
    const char* input = NULL;
    const char* output = NULL;

    int no_convert = 0;
    int show_help = 0;
    int show_version = 0;

    int i;

    /*
        Parse arguments.
    */
    for (i = 1; i < argc; i++)
    {
        if (
            strcmp(argv[i], "-p") == 0 ||
            strcmp(argv[i], "--password") == 0
        )
        {
            if (i + 1 < argc)
                password = argv[++i];
            else
            {
                print_error("Missing password argument.");
                return 1;
            }
        }
        else if (
            strcmp(argv[i], "-i") == 0 ||
            strcmp(argv[i], "--input") == 0
        )
        {
            if (i + 1 < argc)
                input = argv[++i];
            else
            {
                print_error("Missing input file.");
                return 1;
            }
        }
        else if (
            strcmp(argv[i], "-o") == 0 ||
            strcmp(argv[i], "--output") == 0
        )
        {
            if (i + 1 < argc)
                output = argv[++i];
            else
            {
                print_error("Missing output file.");
                return 1;
            }
        }
        else if (
            strcmp(argv[i], "-n") == 0 ||
            strcmp(argv[i], "--no-convert") == 0
        )
        {
            no_convert = 1;
        }
        else if (
            strcmp(argv[i], "-h") == 0 ||
            strcmp(argv[i], "--help") == 0
        )
        {
            show_help = 1;
        }
        else if (
            strcmp(argv[i], "-v") == 0 ||
            strcmp(argv[i], "--version") == 0
        )
        {
            show_version = 1;
        }
        else
        {
            fprintf(
                stderr,
                "\033[31mError:\033[0m Unknown argument: %s\n",
                argv[i]
            );

            return 1;
        }
    }

    /*
        Version should work without -i/-o.
    */
    if (show_version)
    {
        printf("%s\n", VERSION);
        return 0;
    }

    if (show_help || !input || !output)
    {
        print_help();
        return 0;
    }

    /*
        ========================================================
        MP4 -> CRN
        ========================================================
    */

    if (
        ends_with_ignore_case(input, ".mp4") &&
        ends_with_ignore_case(output, ".crn")
    )
    {
        char temp_mp4[MAX_PATH_BUFFER];

        int have_temp = 0;

        const char* target_mp4 = input;

        /*
            FFmpeg conversion.
        */
        if (!no_convert)
        {
            if (!create_temp_mp4(
                    input,
                    temp_mp4,
                    sizeof(temp_mp4)))
            {
                return 1;
            }

            target_mp4 = temp_mp4;
            have_temp = 1;
        }

        /*
            Encrypt.
        */
        if (!create_crn(
                target_mp4,
                output,
                password))
        {
            if (have_temp)
                DeleteFileA(temp_mp4);

            return 1;
        }

        printf(
            "\033[32mSuccess:\033[0m "
            "File encrypted to %s\n",
            output
        );

        if (have_temp)
            DeleteFileA(temp_mp4);

        return 0;
    }

    /*
        ========================================================
        CRN -> MP4
        ========================================================
    */

    if (
        ends_with_ignore_case(input, ".crn") &&
        ends_with_ignore_case(output, ".mp4")
    )
    {
        if (!decrypt_crn(
                input,
                output,
                password))
        {
            return 1;
        }

        printf(
            "\033[32mSuccess:\033[0m "
            "File decrypted to %s\n",
            output
        );

        return 0;
    }

    /*
        Unsupported combination.
    */
    fprintf(
        stderr,
        "\033[31mError:\033[0m "
        "Unsupported format combination. "
        "Use .mp4 -> .crn or .crn -> .mp4\n"
    );

    return 1;
}
```
