name: Production Deployment to Vercel

on:
  workflow_dispatch: # Allows you to manually trigger the workflow

concurrency:
  group: "vercel-prod-deployment-${{ github.ref }}"
  cancel-in-progress: true

env:
  VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
  VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}

jobs:
  Deploy-Production:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v7

      - name: Install pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 9

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: 'pnpm'

      - name: Install Dependencies
        run: pnpm install --frozen-lockfile

      - name: Setup Supabase CLI
        uses: supabase/setup-cli@v1
        with:
          version: latest

      - name: Push Database Migrations to Supabase
        run: supabase link --project-ref ${{ secrets.SUPABASE_PROJECT_ID }} && supabase db push
        env:
          SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
          SUPABASE_DB_PASSWORD: ${{ secrets.SUPABASE_DB_PASSWORD }}
        # This securely connects to your Supabase project using the official Management API.
        # It avoids the common "Transaction Pooler" port 6543 vs 5432 errors.

      - name: Cache Vite & Vercel Build Assets
        uses: actions/cache@v4
        with:
          path: |
            node_modules/.vite
            .vercel/cache
          key: ${{ runner.os }}-vercel-${{ hashFiles('**/pnpm-lock.yaml') }}-${{ github.sha }}
          restore-keys: |
            ${{ runner.os }}-vercel-${{ hashFiles('**/pnpm-lock.yaml') }}-
            ${{ runner.os }}-vercel-

      - name: Install Vercel CLI
        run: npm install -g vercel@latest

      - name: Pull Vercel Environment Information
        run: vercel pull --yes --environment=production --token=${{ secrets.VERCEL_TOKEN }}

      - name: Build Project Artifacts
        run: vercel build --prod --token=${{ secrets.VERCEL_TOKEN }}

      - name: Deploy Project Artifacts to Vercel
        run: vercel deploy --prebuilt --prod --token=${{ secrets.VERCEL_TOKEN }}