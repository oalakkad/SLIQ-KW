import { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL as string;
const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  let products: any[] = [];
  let categories: any[] = [];

  try {
    const productsRes = await fetch(`${API_URL}/products/sitemap/`);
    if (productsRes.ok) products = await productsRes.json();
  } catch {}

  try {
    const categoriesRes = await fetch(`${API_URL}/categories/sitemap/`);
    if (categoriesRes.ok) categories = await categoriesRes.json();
  } catch {}

  return [
    { url: SITE_URL, lastModified: new Date(), priority: 1 },
    ...categories.map((c: any) => ({
      url: `${SITE_URL}/category/${c.slug}`,
      lastModified: c.updated_at ?? new Date(),
      priority: 0.7,
    })),
    ...products.map((p: any) => ({
      url: `${SITE_URL}/product/${p.slug}`,
      lastModified: p.updated_at,
      priority: 0.8,
    })),
  ];
}
