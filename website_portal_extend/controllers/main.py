# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from urlparse import urlparse, parse_qs
from urllib import urlencode
from odoo import http
from odoo.http import request
from odoo import tools
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.tools.translate import _


class WebsiteAccount(http.Controller):

    @http.route(['/my', '/my/home'], type='http', auth='public', website=True,
                csrf=False)
    def account(self):
        partner = request.env.user.partner_id

        # get customer sales rep
        if partner.user_id:
            sales_rep = partner.user_id
        else:
            sales_rep = False
        values = {'sales_rep': sales_rep,
                  'company': request.website.company_id,
                  'user': request.env.user
                  }
        return request.render('website_portal.account', values)

    @http.route(['/my/account'], type='http', auth='user', website=True,
                csrf=False)
    def details(self, redirect=None, **post):
        partner = request.env['res.users'].browse(request.uid).partner_id
        values = {'error': {},
                  'error_message': []
                  }

        if post:
            error, error_message = self.details_form_validate(post)
            values.update({'error': error, 'error_message': error_message})
            values.update(post)
            if not error:
                post.update({'zip': post.pop('zipcode', '')})
                partner.sudo().write(post)
                if redirect:
                    return request.redirect(redirect)
                return request.redirect('/my/home')

        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])

        values.update({'partner': partner,
                       'countries': countries,
                       'states': states,
                       'has_check_vat': hasattr(request.env['res.partner'],
                                                'check_vat'),
                       'redirect': redirect,
                       })
        return request.render('website_portal.details', values)

    def details_form_validate(self, data):
        error = dict()
        error_message = []

        mandatory_billing_fields = ['name', 'phone', 'email', 'street2',
                                    'city', 'country_id']

        # Validation
        for field_name in mandatory_billing_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'

        # email validation
        if not tools.single_email_re.match(data.get('email', '')):
            error['email'] = 'error'
            error_message.append(_('Invalid Email! Please enter a valid email'
                                   'address.'))

        # vat validation
        if (data.get('vat') and
                hasattr(request.env['res.partner'], 'check_vat')):
            if request.website.company_id.vat_check_vies:
                # force full VIES online check
                check_func = request.env['res.partner'].vies_vat_check
            else:
                # quick and partial off-line checksum validation
                check_func = request.env['res.partner'].simple_vat_check
            vat_country, vat_number = request.env['res.partner']._split_vat(
                data.get('vat'))
            if not check_func(vat_country, vat_number):  # simple_vat_check
                error['vat'] = 'error'
        # error message for empty required fields
        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))

        return error, error_message


class AuthSignup(AuthSignupHome):

    def redirect(self, res, **kw):
        redirect = kw.get('redirect', '')
        if request.session.uid and (not redirect or '/web?' in redirect):
            params = parse_qs(urlparse(redirect).query, keep_blank_values=True)
            return_url = params.pop('redirect', ['/'])[0]
            if '/web?' in return_url:
                return_url = '/'
            return_url = '%s?%s' % (return_url, urlencode(params))
            return http.redirect_with_hash(return_url)
        return res

    @http.route(website=True, auth="public")
    def web_login(self, *args, **kw):
        res = super(AuthSignup, self).web_login(*args, **kw)
        return self.redirect(res, **kw)

    @http.route('/web/signup', type='http', auth='public', website=True,
                csrf=False)
    def web_auth_signup(self, *args, **kw):
        res = super(AuthSignup, self).web_auth_signup(*args, **kw)
        return self.redirect(res, **kw)
