CC = gcc
DB-CFLAGS = -Wall -Wextra -fsanitize=address
CFLAGS = -lm

SRC_ALGO = src/algo/utils.c src/algo/path.c src/algo/darray.c
OBJ = ${SRC_ALGO:.c=.o}

all: algo

algo: ${OBJ}
	${CC} ${OBJ} -o build/$@ ${CFLAGS} ${DB-CFLAGS}

src/algo/%.o: src/algo/%.c
	${CC} -c $< -o $@ ${DB-CFLAGS}

.PHONY: clean

clean:
	${RM} build/*
