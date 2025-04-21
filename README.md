## SmartEdQA Project

### Installation
- upgrade your setup tools
``
pip install --upgrade pip setuptools wheel
``

then `` brew install postgresql `` 

you may opt to have this one installed too:
`` pip install absl-py==0.10.0 ``

make sure python versions are:
- python 3.7
- python 3.8
- python 3.9

others would throw a setup tool wheel error.

the next step would be `` rasa init ``. 

leave the defaults as they're so as the project directory is as.
when asked if you want to train a model say no.

do run `` rasa train `` if any changes are made to the code.

install rasa and `` rasa init `` it to have the bareback directories before you begin your project.

## Order of running

the order:
i. mcq service
```
python3 -m uvicorn mcq_service.app:app --port 8001
```

ii. short answer service
```
python3 -m uvicorn short_app:app --port 8002
```

iii. start the http server for ui
```
python3 -m http.server 8000
```

iv. start rasa  server
```
rasa run --enable-api --cors "*"
```

v. start the rasa action server
```
rasa run actions --port 5055
```

you also require different virtual environments for the short and mcq engine, and rasa as they have different dependency issues. 

these requirements file can be installed in said environments by a command:

``` 
pip install -r requirements.txt
```

special shout out to [Prof Nyberg Eric](https://www.cs.cmu.edu/~ehn/) for his guidance and mentorship.!!

