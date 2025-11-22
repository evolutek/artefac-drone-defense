CC = gcc
CPPFLAGS := -I src
CFLAGS := -Wall -Wextra -Werror -g -march=native -fsanitize=address 
LDFLAGS := -lm

SRC = $(wildcard src/**/*.c)
OBJ = $(SRC:.c=.o)

TARGET := build/algo

.PHONY: clean all

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^

clean:
	$(RM) $(TARGET)
	$(RM) $(OBJ)
