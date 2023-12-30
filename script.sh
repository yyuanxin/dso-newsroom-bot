#!/bin/bash

FILE=python-package.zip
if [ -f "$FILE" ]; then
    echo "$FILE exists."
		rm -r "$FILE"
fi

pip3 install --target ./package -r requirements.txt
cd package
zip -r ../python-package.zip .
cd ..
zip python-package.zip lambda_function.py classes.py