# Example Vulnerable Flask

A minimal web app developed with [Flask](http://flask.pocoo.org/) framework which is intentionally vulnerable.

## Burp Suite

Burp Suite is a good tool for intercepting requests and general testing. You can find the community edition [here](https://portswigger.net/burp/communitydownload) for download.


## How to Run

- Step 1: Make sure you have Python

- Step 2: Install the requirements: `pip install -r requirements.txt`

- Step 3: Go to this app's directory and run `python app.py`



## Details about This Toy App

There are three tabs in this toy app

- **Public**: this is a page which can be accessed by anyone, no matter if the user has logged in or not.

- **Private**: Only logged-in user can access this page. Otherwise the user will get a 401 error page.

- **Admin Page**: This part is only open to the user who logged in as "Admin". In this tab, the administrator can manage accounts (list, delete, or add).


The following accounts exist on the site:
- `admin:admin`
- `test:123456`
- `user1:user1`
- `user2:user2`
- `user3:user3`

You can also delete or add accounts after you log in as ***admin***.

