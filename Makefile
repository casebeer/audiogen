
default:

docs: README.html

README.html: README.rst
	pandoc $^ > $@

clean:
	find . -type f -name '*.pyc' -print0 | xargs -0 rm -f -- 
	rm -rf *.egg-info
	rm -f README.html
