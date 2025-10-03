
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    FILE *src, *dest;
    char buffer[1024];
    size_t n;
    if (argc != 3) {
        fprintf(stderr, "Usage: %s source_file target_file\n", argv[0]);
        exit(1);
    }
    src = fopen(argv[1], "r");
    if (src == NULL) {
        perror("Failed to open source file");
        exit(1);
    }
    dest = fopen(argv[2], "a");
    if (dest == NULL) {
        perror("Failed to open target file");
        fclose(src);
        exit(1);
    }
    while ((n = fread(buffer, 1, sizeof(buffer), src)) > 0) {
        fwrite(buffer, 1, n, dest);
    }

    fclose(src);
    fclose(dest);

    printf("Appended contents of '%s' to '%s'.\n", argv[1], argv[2]);
    return 0;
}
