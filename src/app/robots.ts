import type { MetadataRoute } from "next";

// Private app: never crawled or indexed.
export default function robots(): MetadataRoute.Robots {
  return { rules: { userAgent: "*", disallow: "/" } };
}
