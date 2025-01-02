class VisaBookingApp:

    def __init__(self):
        
        self.visa_types = {
            "Tourist Visa": 100,
            "Business Visa": 200,
            "student Visa": 150,
            "Work Visa": 250,
        }

        self.bookings = []
    
    def display_menu(self):

        print("\n=== Visa Booking App ===")

        print("1. View Availability Visa Types")

        print("2. Book a Visa")

        print("3. View My Bookings")

        print("4. Exit")

    def view_visa_types(self):

        print("\nAvailable Visa Types:")

        for visa, price in self.visa_types.items():

            print(f" - {visa}: ${price}")
    
    def book_visa(self):

        print("\nAvailable Visa Types:")

        for i, (visa, price) in enumerate(self.visa_types.items(), start=1):

            print(f"{i}. {visa}: ${price}")
        
        choice = input("\nEneter the number of the visa you want to book: ")

        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(self.visa_types):

            print("Invalid choice. Please Try again.")

            return
        
        visa_name = list(self.visa_types.keys())[int(choice) - 1]

        applicant_name = input("Enter your name: ")

        passport_number = input("Enter your passport number: ")

        booking = {
            "Visa" : visa_name,
            "Applicant" : applicant_name,
            "Passport" : passport_number
        }

        self.bookings.append(booking)

        print(f"\nVisa for {visa_name} successfully booked for {applicant_name}!")

    def view_bookings(self):

        if not self.bookings:

            print("\nNo bookings found.")

            return
        print("\nYour Bookings:")

        for i, booking in enumerate(self.bookings, start=1):

            print(f"{i}. {booking['Visa']} - {booking['Applicant']} (Passport: {booking['Passport']})")

    def run(self):

        while True:

            self.display_menu()

            choice = input("Enter your choice: ")

            if choice == "1":
                
                self.view_visa_types()
            
            elif choice == "2":

                self.book_visa()
            
            elif choice == "3":
                
                self.view_bookings()
            
            elif choice == "4":

                print("\nThank you for using the Visa Booking App. Goodbye!")

                break
            
            else:

                print("\nInvalid choice. Please try again.")

#Run the app
if __name__ == "__main__":

    app = VisaBookingApp()

    app.run()





