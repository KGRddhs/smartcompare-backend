# Qaren landing page — nginx static site for Railway deploy
# Per Bundle D Task A6-refit (dispatcher decision 2026-05-23): Ahmed chose
# Railway over Vercel for single-vendor consolidation. Image builds the
# static HTML/CSS + .well-known directory under nginx:alpine.
#
# Railway assigns the listening port via $PORT env var at runtime. The
# nginx:alpine official image supports template-based config substitution
# under /etc/nginx/templates/*.conf.template — envsubst runs on boot to
# render real config under /etc/nginx/conf.d/.

FROM nginx:1.27-alpine

# Remove the default nginx config so our template is the only server block.
RUN rm /etc/nginx/conf.d/default.conf

# Copy our nginx config template (envsubst will render $PORT at boot).
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Copy static site files into nginx web root.
# Exclude README.md, Dockerfile, railway.toml, vercel.json, nginx.conf.template
# so they don't get served as web content.
COPY index.html /usr/share/nginx/html/
COPY privacy.html /usr/share/nginx/html/
COPY terms.html /usr/share/nginx/html/
COPY support.html /usr/share/nginx/html/
COPY .well-known /usr/share/nginx/html/.well-known

# Railway's HTTP edge sends traffic to $PORT; expose it dynamically.
# Default 8080 for local testing (docker run -p 8080:8080 qaren-landing).
ENV PORT=8080
EXPOSE 8080

# nginx:alpine entrypoint already runs envsubst on templates + nginx -g daemon off.
# No CMD override needed.
