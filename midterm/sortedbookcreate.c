#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "student.h"

#define MAX_BOOKS 100

int main(int argc, char *argv[])
{
    struct student arr[MAX_BOOKS];
    int n = 0;
    FILE *fp;
    int i, j;

    if (argc != 2) {
        fprintf(stderr, "How to use: %s FileName\n", argv[0]);
        return 1;
    }

    fp = fopen(argv[1], "wb");
    if (fp == NULL) {
        perror("fopen");
        return 1;
    }

    printf("%-4s %-15s %-15s %-6s %-11s %-7s\n",
           "id", "bookname", "author", "year", "numofborrow", "borrow");
    printf("example ) 1 1984 George 1949 7 0\n\n");

    while (n < MAX_BOOKS &&
           scanf("%d %29s %29s %d %d %d",
                 &arr[n].id,
                 arr[n].name,
                 arr[n].author,
                 &arr[n].year,
                 &arr[n].borrow_count,
                 &arr[n].borrowed) == 6) {
        n++;
    }

    for (i = 0; i < n - 1; i++) {
        for (j = i + 1; j < n; j++) {
            if (arr[i].year < arr[j].year) {
                struct student tmp = arr[i];
                arr[i] = arr[j];
                arr[j] = tmp;
            }
        }
    }

    for (i = 0; i < n; i++) {
        arr[i].id = i + 1;
        fwrite(&arr[i], sizeof(struct student), 1, fp);
    }

    fclose(fp);
    return 0;
}

