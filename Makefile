APPENGINE_BASE=https://storage.googleapis.com/appengine-sdks/featured
APPENGINE_SDK=google_appengine_1.9.35.zip
ENV=../.hashtagtodo
GENERATED=generated
GENERATED_PYTHON=$(GENERATED)/python
SDK_PATH=$(shell ./tools/realpath $(ENV)/google_appengine)
STATIC=todo/static

.PHONY: all
all: app $(ENV)

.PHONY: clean
clean:
	rm -rf $(GENERATED)
	rm -f $(MAPREDUCE)
	find . -name \*.pyc | xargs rm -f
	rm -rf $(STATIC)/bower_components
	rm -rf $(STATIC)/node_modules

.PHONY: superclean
superclean: clean
	rm -rf $(ENV)

$(ENV):
	mkdir -p $(ENV)
	cd $(ENV) && wget -q $(APPENGINE_BASE)/$(APPENGINE_SDK)
	cd $(ENV) && unzip $(APPENGINE_SDK)

.PHONY: production
production:
	$(SDK_PATH)/appcfg.py -A hashtagtodo update .

.PHONY: develop
develop: all
	$(SDK_PATH)/dev_appserver.py --log_level=debug app.yaml

.PHONY: app
app: $(GENERATED_PYTHON) $(STATIC)/bower_components

$(STATIC)/bower_components: $(STATIC)/bower.json
	cd $(STATIC) && npm install

$(GENERATED_PYTHON): requirements.txt
	rm -rf $(GENERATED_PYTHON)
	mkdir -p $(GENERATED_PYTHON)
	pip install -r requirements.txt -t $(GENERATED_PYTHON)
	patch -p1 <authomatic.patch
