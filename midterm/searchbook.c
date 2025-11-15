#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "student.h"

int main(int argc, char *argv[])
{
    struct student rec;
    FILE *fp;
    char target[30];
    int found = 0;

    if (argc != 2) {
        fprintf(stderr, "How to use: %s FileName\n", argv[0]);
        return 1;
    }

    fp = fopen(argv[1], "rb");
    if (fp == NULL) {
        perror("fopen");
        return 1;
    }

    printf("input name of book ) ");
    scanf("%29s", target);

    printf("\n");

    while (fread(&rec, sizeof(rec), 1, fp) == 1) {
        if (strcmp(rec.name, target) == 0) {
            if (!found) {
                printf("%-4s %-15s %-15s %-6s %-11s %-7s\n",
                       "id", "bookname", "author", "year", "numofborrow", "borrow");
            }
            found = 1;
            printf("%-4d %-15s %-15s %-6d %-11d %-7s\n",
                   rec.id,
                   rec.name,
                   rec.author,
                   rec.year,
                   rec.borrow_count,
                   rec.borrowed ? "True" : "False");
        }
    }

    if (!found) {
        printf("not found book name : '%s'\n", target);
    }

    fclose(fp);
    return 0;
}

