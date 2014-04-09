
default: sdist

sdist:
	python setup.py sdist

docs: README.html

README.html: README.rst
	pandoc $^ > $@

register:
	python setup.py register

upload: 
	python setup.py sdist upload --sign -r https://pypi.python.org/pypi

clean:
	find . -type f -name '*.pyc' -print0 | xargs -0 rm -f -- 
	rm -rf *.egg-info
	rm -f README.html
	rm -rf dist/
