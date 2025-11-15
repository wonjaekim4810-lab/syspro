#include <stdio.h>
#include <stdlib.h>
#include "student.h"

int main(int argc, char *argv[])
{
    struct student rec;
    FILE *fp;
    int mode, bookid;

    if (argc != 2) {
        fprintf(stderr, "How to use: %s FileName\n", argv[0]);
        exit(1);
    }

    fp = fopen(argv[1], "rb+");
    if (fp == NULL) {
        perror("fopen");
        exit(1);
    }

    printf("0 bookId: borrow book, 1 bookId: return book ) ");
    scanf("%d %d", &mode, &bookid);

    if (mode != 0 && mode != 1) {
        printf("Invalid mode.\n");
        fclose(fp);
        return 0;
    }

    fseek(fp, (bookid - 1) * sizeof(rec), SEEK_SET);
    if (fread(&rec, sizeof(rec), 1, fp) != 1) {
        printf("No such book.\n");
        fclose(fp);
        return 0;
    }

    if (mode == 0) {
        if (rec.borrowed == 1) {
            printf("You cannot borrow below book since it has been booked.\n");
        } else {
            rec.borrowed = 1;
            rec.borrow_count++;
            fseek(fp, (bookid - 1) * sizeof(rec), SEEK_SET);
            fwrite(&rec, sizeof(rec), 1, fp);
            printf("You've got bellow book.\n");
        }
    } else {
        if (rec.borrowed == 0) {
            printf("You haven't borrowed below book.\n");
        } else {
            rec.borrowed = 0;
            fseek(fp, (bookid - 1) * sizeof(rec), SEEK_SET);
            fwrite(&rec, sizeof(rec), 1, fp);
            printf("You've returned bellow book.\n");
        }
    }

    printf("%-4s %-15s %-15s %-6s %-10s %-7s\n",
           "id", "bookname", "author", "year", "numofborrow", "borrow");
    printf("%-4d %-15s %-15s %-6d %-10d %-7s\n",
           rec.id, rec.name, rec.author,
           rec.year, rec.borrow_count,
           rec.borrowed ? "True" : "False");

    fclose(fp);
    return 0;
}

