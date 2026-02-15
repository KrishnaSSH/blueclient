self hostable reddit client
 ![](assets/mockup.png)
## How to run 
```sh
python -m venv venv
```
```sh
source venv/bin/activate
```
```sh
 gunicorn -w 4 -b 0.0.0.0:8000 app:app
```



