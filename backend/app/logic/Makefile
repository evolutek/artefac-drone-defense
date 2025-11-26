CC = gcc
CPPFLAGS := -I src
CFLAGS := -Wall -Wextra -Werror -march=native  -O0 -g -fsanitize=address 
LDFLAGS := -lm -lpthread 

SRC = $(wildcard src/**/*.c) src/main.c
OBJ = $(SRC:.c=.o)

TARGET := build/algo

.PHONY: clean all

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^

clean:
	$(RM) $(TARGET)
	$(RM) $(OBJ)
