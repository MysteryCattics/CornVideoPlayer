#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/stat.h>
#include <libgen.h>
#include <ctype.h>
#include <openssl/evp.h>
#include <openssl/kdf.h>
#include <openssl/rand.h>
#include <openssl/err.h>

#define HEADER "CORNFORMATv1----"
#define HEADER_LEN 16
#define SALT_LEN 16
#define IV_LEN 16
#define KEY_LEN 32
#define PBKDF2_ITERATIONS 200000

const char *version = "v1.0.0";

void handleErrors(void) {
    ERR_print_errors_fp(stderr);
    exit(1);
}

int makeKey(const char *password, const unsigned char *salt, unsigned char *key) {
    const char *actualPassword = password;
    if (actualPassword == NULL || strlen(actualPassword) == 0) {
        actualPassword = "default_empty_password";
    }

    if (PKCS5_PBKDF2_HMAC(actualPassword, strlen(actualPassword), salt, SALT_LEN, PBKDF2_ITERATIONS, EVP_sha256(), KEY_LEN, key) != 1) {
        return 0;
    }
    return 1;
}

int createDirectories(const char *path) {
    char tmp[1024];
    char *p = NULL;
    size_t len;

    snprintf(tmp, sizeof(tmp), "%s", path);
    len = strlen(tmp);
    if (tmp[len - 1] == '/')
        tmp[len - 1] = 0;
    for (p = tmp + 1; *p; p++)
        if (*p == '/') {
            *p = 0;
            mkdir(tmp, S_IRWXU);
            *p = '/';
        }
    mkdir(tmp, S_IRWXU);
    return 0;
}

char* createCrn(const char *mp4Path, const char *outputPath, const char *password) {
    struct stat st;
    if (stat(mp4Path, &st) != 0) {
        fprintf(stderr, "Файл не найден: %s\n", mp4Path);
        exit(1);
    }

    char *pathCopy = strdup(outputPath);
    char *dirName = dirname(pathCopy);
    if (strcmp(dirName, ".") != 0 && strcmp(dirName, "/") != 0) {
        createDirectories(dirName);
    }
    free(pathCopy);

    FILE *fIn = fopen(mp4Path, "rb");
    if (!fIn) {
        perror("Error opening input file");
        exit(1);
    }

    fseek(fIn, 0, SEEK_END);
    long fileSize = ftell(fIn);
    fseek(fIn, 0, SEEK_SET);

    unsigned char *data = malloc(fileSize);
    fread(data, 1, fileSize, fIn);
    fclose(fIn);

    unsigned char salt[SALT_LEN];
    unsigned char iv[IV_LEN];
    unsigned char key[KEY_LEN];

    if (RAND_bytes(salt, SALT_LEN) != 1 || RAND_bytes(iv, IV_LEN) != 1) {
        handleErrors();
    }

    if (!makeKey(password, salt, key)) {
        handleErrors();
    }

    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    if (!ctx) handleErrors();

    if (1 != EVP_EncryptInit_ex(ctx, EVP_aes_256_cfb(), NULL, key, iv))
        handleErrors();

    unsigned char *encrypted = malloc(fileSize + EVP_MAX_BLOCK_LENGTH);
    int len;
    int ciphertextLen;

    if (1 != EVP_EncryptUpdate(ctx, encrypted, &len, data, fileSize))
        handleErrors();
    ciphertextLen = len;

    if (1 != EVP_EncryptFinal_ex(ctx, encrypted + len, &len))
        handleErrors();
    ciphertextLen += len;

    EVP_CIPHER_CTX_free(ctx);

    FILE *fOut = fopen(outputPath, "wb");
    if (!fOut) {
        perror("Error opening output file");
        exit(1);
    }

    fwrite(HEADER, 1, HEADER_LEN, fOut);
    fwrite(salt, 1, SALT_LEN, fOut);
    fwrite(iv, 1, IV_LEN, fOut);
    fwrite(encrypted, 1, ciphertextLen, fOut);
    fclose(fOut);

    free(data);
    free(encrypted);

    return (char*)outputPath;
}

char* decryptCrn(const char *crnPath, const char *outputPath, const char *password) {
    struct stat st;
    if (stat(crnPath, &st) != 0) {
        fprintf(stderr, "Файл не найден: %s\n", crnPath);
        exit(1);
    }

    char *pathCopy = strdup(outputPath);
    char *dirName = dirname(pathCopy);
    if (strcmp(dirName, ".") != 0 && strcmp(dirName, "/") != 0) {
        createDirectories(dirName);
    }
    free(pathCopy);

    FILE *fIn = fopen(crnPath, "rb");
    if (!fIn) {
        perror("Error opening input file");
        exit(1);
    }

    char headerCheck[HEADER_LEN];
    fread(headerCheck, 1, HEADER_LEN, fIn);
    if (memcmp(headerCheck, HEADER, HEADER_LEN) != 0) {
        fprintf(stderr, "Неверный формат файла или заголовок поврежден\n");
        exit(1);
    }

    unsigned char salt[SALT_LEN];
    unsigned char iv[IV_LEN];
    fread(salt, 1, SALT_LEN, fIn);
    fread(iv, 1, IV_LEN, fIn);

    fseek(fIn, 0, SEEK_END);
    long currentPos = ftell(fIn);
    long encryptedSize = currentPos - (HEADER_LEN + SALT_LEN + IV_LEN);
    fseek(fIn, HEADER_LEN + SALT_LEN + IV_LEN, SEEK_SET);

    unsigned char *encryptedData = malloc(encryptedSize);
    fread(encryptedData, 1, encryptedSize, fIn);
    fclose(fIn);

    unsigned char key[KEY_LEN];
    if (!makeKey(password, salt, key)) {
        handleErrors();
    }

    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    if (!ctx) handleErrors();

    if (1 != EVP_DecryptInit_ex(ctx, EVP_aes_256_cfb(), NULL, key, iv))
        handleErrors();

    unsigned char *decryptedData = malloc(encryptedSize + EVP_MAX_BLOCK_LENGTH);
    int len;
    int decryptedLen;

    if (1 != EVP_DecryptUpdate(ctx, decryptedData, &len, encryptedData, encryptedSize))
        handleErrors();
    decryptedLen = len;

    if (1 != EVP_DecryptFinal_ex(ctx, decryptedData + len, &len))
        handleErrors();
    decryptedLen += len;

    EVP_CIPHER_CTX_free(ctx);

    FILE *fOut = fopen(outputPath, "wb");
    if (!fOut) {
        perror("Error opening output file");
        exit(1);
    }
    fwrite(decryptedData, 1, decryptedLen, fOut);
    fclose(fOut);

    free(encryptedData);
    free(decryptedData);

    return (char*)outputPath;
}

int endsWith(const char *str, const char *suffix) {
    if (!str || !suffix) return 0;
    size_t lenstr = strlen(str);
    size_t lensuffix = strlen(suffix);
    if (lensuffix > lenstr) return 0;
    for (size_t i = 0; i < lensuffix; i++) {
        if (tolower((unsigned char)str[lenstr - lensuffix + i]) != tolower((unsigned char)suffix[i]))
            return 0;
    }
    return 1;
}

int main(int argc, char *argv[]) {
    char *password = "";
    char *input = NULL;
    char *output = NULL;
    int noConvert = 0;
    int showHelp = 0;
    int showVersion = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-p") == 0 || strcmp(argv[i], "--password") == 0) {
            if (i + 1 < argc) password = argv[++i];
        } else if (strcmp(argv[i], "-i") == 0 || strcmp(argv[i], "--input") == 0) {
            if (i + 1 < argc) input = argv[++i];
        } else if (strcmp(argv[i], "-o") == 0 || strcmp(argv[i], "--output") == 0) {
            if (i + 1 < argc) output = argv[++i];
        } else if (strcmp(argv[i], "-n") == 0 || strcmp(argv[i], "--no-convert") == 0) {
            noConvert = 1;
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            showHelp = 1;
        } else if (strcmp(argv[i], "-v") == 0 || strcmp(argv[i], "--version") == 0) {
            showVersion = 1;
        }
    }

    const char *helpFormula = 
        "\nUsage:\n"
        "cvp -i <input_file> -p <password> -o <output_file>  \n\n"
        "-p, --password: Password for encryption/decryption (optional).\n"
        "-i, --input: Input file path.\n"
        "-o, --output: Output file path.\n"
        "-n, --no-convert: Don't convert through FFmpeg.\n"
        "-h, --help: Show this message.\n"
        "-v, --version: Show the current version\n\n"
        "Example:\n"
        "cvp -i input.mp4 -p pass123 -o custom_name.crn\n\n"
        "\033[33m Warning: \033[0m If you don't specify a password, the default password will be used.\n"
        "\033[33m Warning: \033[0m FFmpeg is REQUIRED for video conversion.\n";

    if (showHelp || !input || !output) {
        printf("%s", helpFormula);
        return 0;
    }

    if (showVersion) {
        printf("%s\n", version);
        return 0;
    }

    if (endsWith(input, ".mp4") && endsWith(output, ".crn")) {
        char *targetMp4 = input;
        char tempMp4Path[1024] = "";

        if (!noConvert) {
            char template[] = "/tmp/cvp_XXXXXX.mp4";
            int fd = mkstemps(template, 4);
            if (fd == -1) {
                perror("Error creating temp file");
                return 1;
            }
            close(fd);
            strcpy(tempMp4Path, template);

            printf("Processing video with FFmpeg...\n");
            char ffmpegCmd[2048];
            snprintf(ffmpegCmd, sizeof(ffmpegCmd), "ffmpeg -i \"%s\" -vcodec libx264 -acodec aac -y \"%s\" > /dev/null 2>&1", input, tempMp4Path);
            
            int ret = system(ffmpegCmd);
            if (ret != 0) {
                fprintf(stderr, "\033[31mFFmpeg Error:\033[0m Command failed\n");
                if (strlen(tempMp4Path) > 0) unlink(tempMp4Path);
                return 1;
            }
            targetMp4 = tempMp4Path;
        }

        createCrn(targetMp4, output, password);
        printf("\033[32mSuccess:\033[0m File encrypted to %s\n", output);

        if (strlen(tempMp4Path) > 0) {
            unlink(tempMp4Path);
        }
    } else if (endsWith(input, ".crn") && endsWith(output, ".mp4")) {
        decryptCrn(input, output, password);
        printf("\033[32mSuccess:\033[0m File decrypted to %s\n", output);
    } else {
        printf("\033[31mError:\033[0m Unsupported format combination. Use .mp4 -> .crn or .crn -> .mp4\n");
    }

    return 0;
}
