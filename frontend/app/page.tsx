import { redirect } from "next/navigation";

// No marketing landing page: the app opens straight on sign-in
// (the login page forwards already signed-in users to /home).
export default function Root() {
  redirect("/login");
}
