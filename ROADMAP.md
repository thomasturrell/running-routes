# Running Routes - Improvement Roadmap

This document outlines the planned improvements for the Running Routes project as specified in Issue #32.

## ✅ Completed in This PR

### 1. Hugo Migration Foundation
- [x] Install Hugo and set up basic site structure
- [x] Configure Ananke theme with appropriate settings
- [x] Migrate core content (homepage, about page)
- [x] Create Bob Graham Round route page
- [x] Set up GPX viewer shortcode (replaces Jekyll include)
- [x] Copy GPX assets to Hugo static directory
- [x] Create GitHub Actions workflow for Hugo deployment (disabled by default)

### 2. Documentation Improvements
- [x] Add development setup documentation (DEVELOPMENT.md)
- [x] Create this roadmap document
- [x] Update with clear migration path

### 3. Basic Analytics Setup
- [x] Add Google Analytics configuration to Hugo
- [x] Configure privacy-compliant settings
- [x] Ready for tracking ID when needed

## 🚧 In Progress / Next Phase

### 1. Complete Hugo Migration
- [ ] Migrate remaining fell running routes (Ramsay Round, Paddy Buckley Round, Allermuir Hill Race)
- [ ] Create trail and road running section templates
- [ ] Customize theme for better mobile experience
- [ ] Add search functionality
- [ ] Optimize images and assets
- [ ] Test all GPX viewer functionality
- [ ] Validate all links and downloads

### 2. Performance Optimizations
- [ ] Enable asset minification in Hugo
- [ ] Set up proper caching headers
- [ ] Optimize images (WebP conversion)
- [ ] Implement lazy loading for maps
- [ ] Add service worker for offline capability

### 3. SPA Transition Preparation
- [ ] Research React/Vue/Svelte options for interactive features
- [ ] Plan API structure for dynamic content
- [ ] Design component architecture
- [ ] Evaluate SSR/SSG solutions (Next.js, Nuxt.js, SvelteKit)
- [ ] Create prototype for route filtering and search

## 🔮 Future Phases

### Phase 3: Enhanced Features
- [ ] Strava API integration for real-time data
- [ ] User route submissions and management
- [ ] Interactive route planning tools
- [ ] Advanced filtering and search
- [ ] Route comparison features

### Phase 4: Platform Migration
- [ ] Evaluate hosting platforms (Vercel, Netlify, Cloudflare Pages)
- [ ] Set up CI/CD pipelines
- [ ] Configure custom domain and DNS
- [ ] Implement fallback routing for SPA features

### Phase 5: Data Improvements
- [ ] Evaluate LiDAR elevation data sources
- [ ] Implement elevation profile smoothing
- [ ] Add validation against GPS/altimeter data
- [ ] Create elevation comparison tools

### Phase 6: Advanced Features
- [ ] Accessibility improvements (WCAG compliance)
- [ ] Multi-language support
- [ ] Advanced analytics and user insights
- [ ] Community features (comments, ratings)
- [ ] Mobile app considerations

## 🎯 Success Metrics

- **Performance**: Lighthouse score > 90 for all categories
- **Accessibility**: WCAG 2.1 AA compliance
- **User Experience**: < 3 second load times, intuitive navigation
- **Content**: All existing routes migrated with improved presentation
- **Developer Experience**: Easy local development, automated deployments

## 🚀 Migration Timeline

1. **Phase 1** (This PR): Foundation and basic migration
2. **Phase 2** (Next 2-3 PRs): Complete content migration and optimization
3. **Phase 3** (Future): SPA transition and advanced features
4. **Phase 4** (Future): Platform migration and scaling

## 📝 Notes

- Hugo setup runs parallel to Jekyll to avoid breaking production
- Switch to Hugo by changing GitHub Actions workflow trigger
- SPA transition should maintain SEO benefits through SSR/SSG
- All changes should maintain backward compatibility for existing links