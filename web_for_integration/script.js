document.addEventListener('DOMContentLoaded', () => {

    /* ==========================================================================
       Header Scroll & Mobile Menu Toggle
       ========================================================================== */
    const header = document.getElementById('site-header');
    const menuToggle = document.getElementById('menu-toggle-btn');
    const navMenu = document.getElementById('navigation-menu-links');
    const navLinks = document.querySelectorAll('.nav-link');

    // Add sticky styling on scroll
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });

    // Toggle Mobile Navigation Menu
    menuToggle.addEventListener('click', () => {
        navMenu.classList.toggle('active');
        const icon = menuToggle.querySelector('i');
        if (navMenu.classList.contains('active')) {
            icon.className = 'fa-solid fa-xmark';
        } else {
            icon.className = 'fa-solid fa-bars';
        }
    });

    // Close menu when clicking navigation links
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            navMenu.classList.remove('active');
            menuToggle.querySelector('i').className = 'fa-solid fa-bars';
        });
    });

    /* ==========================================================================
       Scroll Spy for Navigation Links
       ========================================================================== */
    const sections = document.querySelectorAll('section');
    
    window.addEventListener('scroll', () => {
        let currentSectionId = '';
        const scrollPosition = window.scrollY + 100; // Offset for header height

        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                currentSectionId = section.getAttribute('id');
            }
        });

        if (currentSectionId) {
            navLinks.forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href') === `#${currentSectionId}`) {
                    link.classList.add('active');
                }
            });
        }
    });

    /* ==========================================================================
       Search Bar Interactivity
       ========================================================================== */
    const searchInput = document.getElementById('search-bar-input');
    const searchDropdown = document.getElementById('search-dropdown-results');
    
    // Mock data for university-wide search
    const searchableDatabase = [
        { name: "Computer Science Engineering", url: "#academics", type: "Degree" },
        { name: "Artificial Intelligence Lab", url: "#research", type: "Research" },
        { name: "Admissions Fall 2026 Process", url: "#admissions", type: "Admissions" },
        { name: "Scholarships and Tuition Fees", url: "#admissions", type: "Admissions" },
        { name: "Electrical & Electronics Engineering", url: "#academics", type: "Degree" },
        { name: "Business Administration & MBA", url: "#academics", type: "Degree" },
        { name: "Startup Incubation Catalysts", url: "#research", type: "Research" },
        { name: "Sports Complex & Athletic Stadium", url: "#campus-life", type: "Campus" },
        { name: "Student Hostels & Residential Housing", url: "#campus-life", type: "Campus" },
        { name: "Alumni Network & Career Placements", url: "#placements", type: "Placements" },
        { name: "Quantum Cryptography Symposium", url: "#events", type: "Events" }
    ];

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        if (query.length < 2) {
            searchDropdown.style.display = 'none';
            return;
        }

        const filtered = searchableDatabase.filter(item => 
            item.name.toLowerCase().includes(query) || item.type.toLowerCase().includes(query)
        );

        if (filtered.length > 0) {
            searchDropdown.innerHTML = filtered.map(item => `
                <a href="${item.url}">
                    <strong>[${item.type}]</strong> ${item.name}
                </a>
            `).join('');
            searchDropdown.style.display = 'flex';
        } else {
            searchDropdown.innerHTML = `<a href="#contact" style="color: var(--text-muted); cursor: default;">No results found. Contact Admissions?</a>`;
            searchDropdown.style.display = 'flex';
        }
    });

    // Close search dropdown on click outside
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
            searchDropdown.style.display = 'none';
        }
    });

    /* ==========================================================================
       Interactive Counters (Statistics Section)
       ========================================================================== */
    const statCards = document.querySelectorAll('.stat-card');
    let countersStarted = false;

    const startCounters = () => {
        statCards.forEach(card => {
            const numElement = card.querySelector('.stat-number');
            const target = parseInt(card.getAttribute('data-target'), 10);
            const suffix = card.getAttribute('data-suffix') || '';
            const duration = 2000; // Animation duration in ms
            const stepTime = Math.max(Math.floor(duration / target), 15);
            
            let currentNum = 0;
            const stepSize = Math.max(Math.ceil(target / (duration / stepTime)), 1);

            const timer = setInterval(() => {
                currentNum += stepSize;
                if (currentNum >= target) {
                    currentNum = target;
                    clearInterval(timer);
                }
                // Formatting logic with commas for 15,000
                numElement.textContent = currentNum.toLocaleString() + suffix;
            }, stepTime);
        });
    };

    // Scroll Observer to trigger counters once visible
    const observerOptions = {
        root: null,
        threshold: 0.3
    };

    const statsObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !countersStarted) {
                countersStarted = true;
                startCounters();
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    const statsSection = document.getElementById('statistics-highlights');
    if (statsSection) {
        statsObserver.observe(statsSection);
    }

    /* ==========================================================================
       Tab Switcher (About Section)
       ========================================================================== */
    const tabButtons = document.querySelectorAll('#about-tabs-nav .tab-btn');
    const tabContents = document.querySelectorAll('.about-section .tab-content');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            // Deactivate all buttons
            tabButtons.forEach(b => b.classList.remove('active'));
            // Hide all tab panels
            tabContents.forEach(c => c.classList.remove('active'));

            // Activate current
            btn.classList.add('active');
            document.getElementById(`tab-${targetTab}`).classList.add('active');
        });
    });

    /* ==========================================================================
       Lightbox Image Gallery (Campus Life Section)
       ========================================================================== */
    const galleryItems = document.querySelectorAll('#campus-life-gallery .gallery-item');
    const lightbox = document.getElementById('gallery-lightbox');
    const lightboxImg = document.getElementById('lightbox-main-img');
    const lightboxCaption = document.getElementById('lightbox-img-caption');
    const lightboxClose = document.getElementById('lightbox-close-btn');

    galleryItems.forEach(item => {
        item.addEventListener('click', () => {
            const imageSrc = item.getAttribute('data-image');
            const captionText = item.getAttribute('data-caption');
            
            lightboxImg.src = imageSrc;
            lightboxCaption.textContent = captionText;
            lightbox.style.display = 'block';
            document.body.style.overflow = 'hidden'; // Lock background scrolling
        });
    });

    // Close lightbox
    const closeLightboxModal = () => {
        lightbox.style.display = 'none';
        document.body.style.overflow = '';
    };

    lightboxClose.addEventListener('click', closeLightboxModal);
    lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox) {
            closeLightboxModal();
        }
    });

    /* ==========================================================================
       Testimonials Auto Slider
       ========================================================================== */
    const testimonialSlides = document.querySelectorAll('#testimonial-slider-container .testimonial-slide');
    const sliderDots = document.querySelectorAll('#slider-dots-nav .dot');
    let currentSlide = 0;
    let slideTimer;

    const showSlide = (index) => {
        testimonialSlides.forEach(slide => slide.classList.remove('active'));
        sliderDots.forEach(dot => dot.classList.remove('active'));

        testimonialSlides[index].classList.add('active');
        sliderDots[index].classList.add('active');
        currentSlide = index;
    };

    const nextSlide = () => {
        let index = currentSlide + 1;
        if (index >= testimonialSlides.length) {
            index = 0;
        }
        showSlide(index);
    };

    const startSlideShow = () => {
        slideTimer = setInterval(nextSlide, 5000);
    };

    const stopSlideShow = () => {
        clearInterval(slideTimer);
    };

    // Dots navigation clicks
    sliderDots.forEach(dot => {
        dot.addEventListener('click', () => {
            const index = parseInt(dot.getAttribute('data-index'), 10);
            stopSlideShow();
            showSlide(index);
            startSlideShow();
        });
    });

    // Initialize testimonials slider
    if (testimonialSlides.length > 0) {
        startSlideShow();
    }

    /* ==========================================================================
       Modals Logic (Student Login & Apply Now)
       ========================================================================== */
    const loginModal = document.getElementById('login-modal-box');
    const applyModal = document.getElementById('apply-modal-box');
    
    const loginBtn = document.getElementById('student-login-btn');
    const applyBtn = document.getElementById('apply-now-btn');
    const heroApplyBtn = document.getElementById('hero-apply-btn');
    const quickApplyLink = document.querySelector('.hero-quick-links a[href="#admissions"]');
    
    const loginClose = document.getElementById('login-close-btn');
    const applyClose = document.getElementById('apply-close-btn');

    // Open Login Modal
    loginBtn.addEventListener('click', () => {
        loginModal.classList.add('active');
        document.body.style.overflow = 'hidden';
    });

    // Open Apply Modal
    const openApplyModal = () => {
        applyModal.classList.add('active');
        document.body.style.overflow = 'hidden';
    };
    applyBtn.addEventListener('click', openApplyModal);
    heroApplyBtn.addEventListener('click', openApplyModal);

    // Close Modals
    const closeModal = (modal) => {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    };

    loginClose.addEventListener('click', () => closeModal(loginModal));
    applyClose.addEventListener('click', () => closeModal(applyModal));

    // Close modal on outside click
    window.addEventListener('click', (e) => {
        if (e.target === loginModal) closeModal(loginModal);
        if (e.target === applyModal) closeModal(applyModal);
    });

    // Handle Mock Student Login
    const loginForm = document.getElementById('student-login-form');
    const loginFeedback = document.getElementById('login-feedback-msg');

    loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = document.getElementById('login-id').value;
        const pass = document.getElementById('login-pw').value;

        // Perform mock API loading state
        loginFeedback.className = "login-feedback";
        loginFeedback.textContent = "Verifying credentials...";
        loginFeedback.style.display = "block";

        setTimeout(() => {
            if (email.includes('@aurelia.edu') && pass.length >= 6) {
                loginFeedback.className = "login-feedback success";
                loginFeedback.innerHTML = `<i class="fa-solid fa-circle-check"></i> Sign in successful! Redirecting to student dashboard...`;
                setTimeout(() => {
                    closeModal(loginModal);
                    loginForm.reset();
                    loginFeedback.style.display = "none";
                }, 1500);
            } else {
                loginFeedback.className = "login-feedback error";
                loginFeedback.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> Access Denied. Ensure your email matches '@aurelia.edu' & password is min 6 chars.`;
            }
        }, 1000);
    });

    // Handle Mock Admissions Application
    const applyForm = document.getElementById('apply-form-element');
    const applyFeedback = document.getElementById('apply-feedback-msg');

    applyForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = document.getElementById('apply-name').value;
        const email = document.getElementById('apply-email').value;

        // Mock submission loading
        applyFeedback.className = "apply-feedback";
        applyFeedback.textContent = "Uploading transcripts & submitting application...";
        applyFeedback.style.display = "block";

        setTimeout(() => {
            applyFeedback.className = "apply-feedback success";
            applyFeedback.innerHTML = `<i class="fa-solid fa-circle-check"></i> Application Submitted! Welcome, ${name}. A confirmation email has been dispatched to ${email}.`;
            setTimeout(() => {
                closeModal(applyModal);
                applyForm.reset();
                applyFeedback.style.display = "none";
            }, 2000);
        }, 1500);
    });

    /* ==========================================================================
       Inquiry Form Submission & Newsletter
       ========================================================================== */
    const inquiryForm = document.getElementById('university-inquiry-form');
    const formToast = document.getElementById('form-toast-msg');

    inquiryForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const name = document.getElementById('form-name').value;
        const email = document.getElementById('form-email').value;
        const program = document.getElementById('form-program').value;
        const submitBtn = document.getElementById('form-submit-btn');

        // Disable button & show loader
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing Inquiry...`;

        setTimeout(() => {
            // Display feedback toast
            formToast.className = "form-feedback-toast success";
            formToast.innerHTML = `<strong>Inquiry Received!</strong> Thank you, ${name}. We have dispatched the prospectus details for ${program.toUpperCase()} to ${email}. Our admissions coordinator will reach out shortly.`;
            formToast.style.display = "block";

            // Reset Form and button state
            inquiryForm.reset();
            submitBtn.disabled = false;
            submitBtn.textContent = "Send Inquiry";

            // Hide toast after 6 seconds
            setTimeout(() => {
                formToast.style.display = "none";
            }, 6000);

        }, 1200);
    });

    // Newsletter footer form
    const newsletterSubmit = document.getElementById('newsletter-submit-btn');
    const newsletterEmail = document.getElementById('newsletter-email');
    const newsFeedback = document.getElementById('newsletter-feedback');

    newsletterSubmit.addEventListener('click', () => {
        const email = newsletterEmail.value.trim();
        if (!email || !email.includes('@') || email.length < 5) {
            newsFeedback.className = "news-feedback error";
            newsFeedback.textContent = "Please provide a valid email address.";
            return;
        }

        newsletterSubmit.disabled = true;
        newsletterSubmit.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;

        setTimeout(() => {
            newsFeedback.className = "news-feedback success";
            newsFeedback.textContent = "Subscribed successfully! Welcome to our news list.";
            newsletterEmail.value = "";
            newsletterSubmit.disabled = false;
            newsletterSubmit.textContent = "Subscribe";
            
            setTimeout(() => {
                newsFeedback.textContent = "";
            }, 4000);
        }, 1000);
    });

    // Virtual campus tour CTA action
    const tourBtn = document.getElementById('hero-tour-btn');
    tourBtn.addEventListener('click', () => {
        alert("Launching Aurelia Virtual Reality 360° Campus Tour... Click OK to enter 3D viewer.");
    });

    // Download Prospectus Button Action
    const prospectusBtn = document.getElementById('download-prospectus-btn');
    prospectusBtn.addEventListener('click', () => {
        const text = prospectusBtn.innerHTML;
        prospectusBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Generating PDF...`;
        setTimeout(() => {
            prospectusBtn.innerHTML = `<i class="fa-solid fa-check"></i> Downloaded!`;
            alert("Aurelia_University_Prospectus_2026.pdf has been downloaded successfully to your local system.");
            setTimeout(() => {
                prospectusBtn.innerHTML = text;
            }, 3000);
        }, 1200);
    });
});
