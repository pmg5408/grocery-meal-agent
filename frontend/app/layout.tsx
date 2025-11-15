import type { Metadata } from "next";
import { Inter, Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

import { UserProvider } from "@/context/userContext";

// This loads the 'Inter' font.
const inter = Inter({ subsets: ["latin"] });

// This sets your browser tab's title.
export const metadata: Metadata = {
  title: "AI Grocery Agent", // You can change this!
  description: "Your AI-powered pantry manager",
};

export default function RootLayout({children,}: Readonly<{children: React.ReactNode;}>) 
{
  return (
    // This is the main <html> tag
    <html lang="en">
      {/* This is the main <body> tag */}
      <body className={inter.className}>
        
        {/*
         * --- THIS IS THE CRITICAL CHANGE ---
         *
         * We are "wrapping" our '{children}' (the rest of the app)
         * with our 'UserProvider'.
         *
         * "Textbook" Explanation: By doing this, we are
         * "installing the PA system in the main lobby."
         *
         * Now, *every* component, on *every* page
         * that renders inside '{children}', will be able to
         * "hear" the broadcast and can use our 'useUser()'
         * hook to get the logged-in user's data.
        */}
        <UserProvider>
          {children}
        </UserProvider>
        
      </body>
    </html>
  );
}
