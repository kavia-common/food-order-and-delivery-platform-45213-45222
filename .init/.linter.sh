#!/bin/bash
cd /home/kavia/workspace/code-generation/food-order-and-delivery-platform-45213-45222/food_delivery_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

