import { json } from "../utils/shared";

export default async function handler(): Promise<Response> {
  return json({ status: "ok", service: "digital-risk-protection-netlify" });
}
