PREFIX=/usr/local
BINDIR=$(PREFIX)/bin

all:
	@echo "Run 'make install' to install the scripts."

install:
	install -d $(BINDIR)
	install -m 755 bkhq brg kys rsn rst $(BINDIR)
	install -m 755 rcl rsy tarx $(BINDIR)

