
#Mehar, CS, Conditionals
#leap year!
year = int(input("Enter a year: "))
right = "YEAR IS A LEAP YEAR! (366 days!)"
wrong = "YEAR IS NOT A LEAP YEAR! (365 days!)"
if year % 4 == 0:
   if year % 100 == 0:
       print(right)
       if year % 400 == 0:
           print (right)
       else:
           print(wrong)
   else:
       print(right)
else:
   print(wrong)
