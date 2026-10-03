import { redirect } from "next/navigation";

import { getAccessToken } from "@/lib/session";

export default async function Home() {
  const token = await getAccessToken();
  redirect(token ? "/dashboard" : "/login");
}
