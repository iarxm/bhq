PREFIX=/usr/local
BINDIR=$(PREFIX)/bin

all:
	@echo "Run 'make install' to install the scripts."

install:
	install -d $(BINDIR)
	install -m 755 bhq $(BINDIR)
	install -m 755 brg kys rst $(BINDIR)
	#install -m 755 rsn rcl rsy tarx $(BINDIR)
